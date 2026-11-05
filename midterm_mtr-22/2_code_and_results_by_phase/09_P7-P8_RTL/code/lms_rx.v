// lms_rx.v -- R3 (adaptive LMS) and R2 (frozen copy) of the project, one symbol per 'en' pulse.  Level L3 (RTL simulation).
// Written line by line after fxp_lib.fxp_receivers (level L2): same formats, same rounding, same saturation, same order of operations.
//
//   r_in, d_in      s16.12   received sample, desired symbol (+-1 = +-4096)
//   accumulator     B_ACC bits, B_ACC-2 fractional bits (range +-2)      updates are added here and saturated
//   coefficient     B_MUL bits, B_MUL-2 fractional bits = the top bits of the accumulator, rounded, saturated
//   products        exact, sum of 16 products exact
//   ya, yf          s16.12   R3 output and R2 output
//   ea, ef          s16.12   d - y (error against the TRUE symbol, used for the MSE counters); R3 updates with ea
//   update          w += mu*e*u with mu = 2^-P (arithmetic shift), rounded to the accumulator LSB (RND = 1 nearest, 0 truncate)
//
// Control (one symbol = one clock with en = 1, results appear on the next clock with valid = 1):
//   use_frozen = 0 : R2 output is copied from R3 (training part, n < N_T)
//   freeze_now = 1 : only on the symbol n = N_T: the coefficients computed for this symbol are stored in the R2 bank
//   use_frozen = 1 : R2 uses the stored bank (n >= N_T)
//
// NOTE FOR LATER (synthesis): all arithmetic of one symbol is written as one clocked block with 64-bit helper functions, to be easy to compare
// with the Python model.  It is a behavioural description; word widths have to be trimmed and the multipliers mapped to DSP48E1 slices
// before any resource or timing number is quoted (phase P9).  At 10^4 symbols/s the path may be a multicycle path.
module lms_rx #(
    parameter L     = 16,
    parameter B_MUL = 12,
    parameter B_ACC = 16,
    parameter P     = 8,
    parameter RND   = 1
)(
    input  wire               clk,
    input  wire               rst,
    input  wire               en,
    input  wire signed [15:0] r_in,
    input  wire signed [15:0] d_in,
    input  wire               freeze_now,
    input  wire               use_frozen,
    output reg  signed [15:0] ya,
    output reg  signed [15:0] yf,
    output reg  signed [15:0] ea,
    output reg  signed [15:0] ef,
    output reg                valid,
    output reg         [31:0] stalls,      // nonzero exact updates that were rounded to zero
    output reg         [31:0] updates      // nonzero exact updates
);
    localparam FR  = 12;
    localparam FA  = B_ACC - 2;
    localparam FM  = B_MUL - 2;
    localparam SHC = FA - FM;              // accumulator -> coefficient shift (>= 0 in all project configurations)
    localparam SHU = 2*FR + P - FA;        // shift of the exact update e*u (frac 24 + P) to the accumulator LSB

    // ---- helper functions (64-bit signed) ----
    function signed [63:0] rsh;            // x * 2^-s, round to nearest (rnd = 1, ties up) or truncate toward -infinity (rnd = 0)
        input signed [63:0] x;
        input integer s;
        input integer rnd;
        begin
            if (s <= 0)       rsh = x <<< (-s);
            else if (rnd == 1) rsh = (x + (64'sd1 <<< (s - 1))) >>> s;
            else              rsh = x >>> s;
        end
    endfunction

    function signed [63:0] sat;            // saturate to an nb-bit two's-complement word
        input signed [63:0] x;
        input integer nb;
        reg signed [63:0] hi, lo;
        begin
            hi  = (64'sd1 <<< (nb - 1)) - 64'sd1;
            lo  = -(64'sd1 <<< (nb - 1));
            sat = (x < lo) ? lo : ((x > hi) ? hi : x);
        end
    endfunction

    // ---- state ----
    reg signed [63:0] acc [0:L-1];         // coefficient accumulators (values fit in B_ACC bits)
    reg signed [63:0] wf  [0:L-1];         // R2 frozen coefficients (fit in B_MUL bits)
    reg signed [63:0] u   [0:L-1];         // delay line (16-bit values)

    // ---- temporaries (blocking assignments, like variables of the Python function) ----
    reg signed [63:0] wm [0:L-1];
    reg signed [63:0] s_a, s_f, t, dlt, e_a, e_f, ya_t, yf_t;
    integer k;
    reg [31:0] inc_u, inc_s;               // per-symbol counts (per tap), added to the counters once

    always @(posedge clk) begin
        valid <= 1'b0;
        if (rst) begin
            for (k = 0; k < L; k = k + 1) begin
                acc[k] = 64'sd0;
                wf[k]  = 64'sd0;
                u[k]   = 64'sd0;
            end
            stalls  <= 32'd0;
            updates <= 32'd0;
        end else if (en) begin
            // 1. delay line
            for (k = L - 1; k > 0; k = k - 1) u[k] = u[k - 1];
            u[0] = r_in;
            // 2. multiplier coefficients = rounded most significant bits of the accumulators
            for (k = 0; k < L; k = k + 1) wm[k] = sat(rsh(acc[k], SHC, RND), B_MUL);
            // 3. R2 bank: copy at n = N_T (before this symbol's update)
            if (freeze_now) for (k = 0; k < L; k = k + 1) wf[k] = wm[k];
            // 4. filters: exact products, exact sum, round to s16.12
            s_a = 64'sd0; s_f = 64'sd0;
            for (k = 0; k < L; k = k + 1) begin
                s_a = s_a + wm[k] * u[k];
                s_f = s_f + wf[k] * u[k];
            end
            ya_t = sat(rsh(s_a, FM, RND), 16);
            yf_t = use_frozen ? sat(rsh(s_f, FM, RND), 16) : ya_t;
            // 5. errors against the true symbol
            e_a = sat(d_in - ya_t, 16);
            e_f = sat(d_in - yf_t, 16);
            // 6. LMS update of R3:  w <- w + mu*e*u
            inc_u = 32'd0; inc_s = 32'd0;
            for (k = 0; k < L; k = k + 1) begin
                t = e_a * u[k];                                           // exact, 24 fractional bits
                dlt = (SHU > 0) ? rsh(t, SHU, RND) : (t <<< (-SHU));
                if (t != 0) begin
                    inc_u = inc_u + 32'd1;                                // counted per tap, as in fxp_receivers
                    if (dlt == 0) inc_s = inc_s + 32'd1;
                end
                acc[k] = sat(acc[k] + dlt, B_ACC);
            end
            updates <= updates + inc_u;
            stalls  <= stalls  + inc_s;
            // 7. outputs
            ya <= ya_t[15:0]; yf <= yf_t[15:0]; ea <= e_a[15:0]; ef <= e_f[15:0];
            valid <= 1'b1;
        end
    end
endmodule
