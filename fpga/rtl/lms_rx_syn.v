// lms_rx_syn.v -- R3 (adaptive LMS) and R2 (frozen copy), synthesisable version of lms_rx.v.  Level L3 (RTL simulation), target of L4.
// Responsible member: Pradeep Kumar (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06; verified bit-exact against fxp_lib.fxp_receivers (L2)
// by fpga/sim/run_lms_syn_tests.py.
//
// Same formats, rounding, saturation and order of operations as lms_rx.v (and fxp_lib.fxp_receivers):
//   r_in, d_in      s16.12   received sample, desired symbol (+-1 = +-4096)
//   accumulator     B_ACC bits, B_ACC-2 fractional bits (range +-2)      updates are added here and saturated
//   coefficient     B_MUL bits, B_MUL-2 fractional bits = the top bits of the accumulator, rounded, saturated
//   products        exact, sum of 16 products exact
//   ya, yf, ea, ef  s16.12   R3 / R2 outputs and errors d - y against the TRUE symbol; R3 updates with ea
//   update          w += mu*e*u with mu = 2^-p_in (shift), rounded to the accumulator LSB (RND = 1 nearest/ties up, 0 truncate)
//
// Differences from lms_rx.v (arithmetic unchanged):
//   * real word widths instead of 64-bit helpers; the 48 products are B_MUL x 16 or 16 x 16 and map to one DSP48E1 each;
//   * one symbol is processed in a fixed sequence of 10 clocks (stages below) instead of one clock, so every stage is short;
//   * mu is a run-time input (p_in, sampled with en) instead of the parameter P;
//   * the rounding constant of the update is added inside the update multiplier (ea*u + half, one DSP48E1 each), and
//     "exact update nonzero" is evaluated as ea != 0 && u != 0, which is the same as ea*u != 0 for integers.
// The whole update of symbol n is written to the accumulators before symbol n+1 starts (en at least 10 clocks apart, checked in
// simulation), so this is plain LMS with no adaptation delay (D = 0), not delayed LMS.
//
// Sequence (clock edge k = the edge where en = 1):
//   k     latch r, d, control and the update rounding constant; shift the delay line; coefficients wm = rounded top bits of the
//         accumulators; R2 bank copy if freeze_now
//   k+1   32 products wm*u and wf*u
//   k+2   partial sums of 4 products
//   k+3   full sums
//   k+4   ya, yf (round to s16.12, saturate)
//   k+5   ea, ef (saturate)                       -> outputs ya, yf, ea, ef hold these values from here on
//   k+6   16 update products with the rounding constant, ea*u + half; nonzero flags
//   k+7   shift by mu (arithmetic, right or left)
//   k+8   limit to B_ACC+1 bits; stall flags
//   k+9   accumulators += update (saturate), stall/update counters; valid = 1 during the following clock
module lms_rx_syn #(
    parameter L     = 16,
    parameter B_MUL = 12,
    parameter B_ACC = 16,
    parameter RND   = 1
)(
    input  wire               clk,
    input  wire               rst,
    input  wire               en,          // one pulse per symbol, at least 10 clocks apart
    input  wire signed [15:0] r_in,
    input  wire signed [15:0] d_in,
    input  wire        [3:0]  p_in,        // mu = 2^-p_in
    input  wire               freeze_now,  // only on the symbol n = N_T: store this symbol's coefficients in the R2 bank
    input  wire               use_frozen,  // 0: R2 output copied from R3 (training), 1: R2 uses the stored bank
    output reg  signed [15:0] ya,
    output reg  signed [15:0] yf,
    output reg  signed [15:0] ea,
    output reg  signed [15:0] ef,
    output reg                valid,
    output wire               busy,        // a symbol is being processed
    output reg         [31:0] stalls,      // nonzero exact updates that were rounded to zero
    output reg         [31:0] updates      // nonzero exact updates
);
    localparam FR  = 12;
    localparam FA  = B_ACC - 2;
    localparam FM  = B_MUL - 2;
    localparam SHC = FA - FM;                       // accumulator -> coefficient shift (B_ACC >= B_MUL)
    localparam NG  = L / 4;                         // groups of 4 products (L must be a multiple of 4)
    localparam PW  = B_MUL + 16;                    // product width
    localparam QW  = PW + 2;                        // sum of 4 products
    localparam SW  = PW + $clog2(L);                // sum of L products
    localparam TW  = 34;                            // update product + rounding constant (|e*u| <= 2^30, constant <= 2^30)
    localparam DW  = 40;                            // update after the mu shift: shifted left by at most 6 (B_ACC = 32, p = 0)

    localparam signed [B_ACC:0] HALF_C = (SHC > 0) ? (64'sd1 <<< (SHC - 1)) : 0;
    localparam signed [B_ACC:0] CHI    =  (64'sd1 <<< (B_MUL - 1)) - 1;
    localparam signed [B_ACC:0] CLO    = -(64'sd1 <<< (B_MUL - 1));
    localparam signed [SW:0]    HALF_Y = 64'sd1 <<< (FM - 1);
    localparam signed [DW-1:0]  DHI    =  (40'sd1 <<< B_ACC) - 1;     // update limited to B_ACC+1 bits (exact, see stage k+8)
    localparam signed [DW-1:0]  DLO    = -(40'sd1 <<< B_ACC);
    localparam signed [B_ACC+1:0] AHI  =  (64'sd1 <<< (B_ACC - 1)) - 1;
    localparam signed [B_ACC+1:0] ALO  = -(64'sd1 <<< (B_ACC - 1));

    // ---- state ----
    reg signed [B_ACC-1:0] acc [0:L-1];             // coefficient accumulators (R3)
    reg signed [B_MUL-1:0] wf  [0:L-1];             // R2 frozen coefficients
    reg signed [15:0]      u   [0:L-1];             // delay line

    // ---- pipeline registers ----
    reg        [8:0]       stg;                     // stg[i] = 1 in the clock after edge k+i
    reg signed [15:0]      d_l;
    reg                    uf_l;
    reg        [5:0]       shr, shl;                // update shift: right by shr (with rounding) or left by shl
    reg signed [TW-1:0]    hr;                      // rounding constant 2^(shr-1) (round to nearest), else 0
    reg signed [B_MUL-1:0] wm  [0:L-1];
    (* use_dsp = "yes" *) reg signed [PW-1:0] pa [0:L-1];
    (* use_dsp = "yes" *) reg signed [PW-1:0] pf [0:L-1];
    reg signed [QW-1:0]    qa  [0:NG-1];
    reg signed [QW-1:0]    qf  [0:NG-1];
    reg signed [SW-1:0]    sa, sf;
    reg signed [15:0]      ya_r, yf_r;
    (* use_dsp = "yes" *) reg signed [TW-1:0] tr [0:L-1];   // ea*u + hr
    reg signed [DW-1:0]    xs  [0:L-1];             // update after the mu shift
    reg signed [B_ACC:0]   dl  [0:L-1];             // limited update
    reg        [L-1:0]     nz, zs;                  // exact update nonzero / nonzero but rounded to zero

    assign busy = |stg;

    // ---- combinational helpers ----
    function signed [B_MUL-1:0] coef;               // round the accumulator to the multiplier word, saturate
        input signed [B_ACC-1:0] a;
        reg   signed [B_ACC:0]   x;
        begin
            x = a;
            if (SHC > 0) x = RND ? ((x + HALF_C) >>> SHC) : (x >>> SHC);
            coef = (x > CHI) ? CHI[B_MUL-1:0] : ((x < CLO) ? CLO[B_MUL-1:0] : x[B_MUL-1:0]);
        end
    endfunction

    function signed [15:0] ysat;                    // sum (frac 12 + FM) -> s16.12, round, saturate
        input signed [SW-1:0] s;
        reg   signed [SW:0]   x;
        begin
            x = s;
            x = RND ? ((x + HALF_Y) >>> FM) : (x >>> FM);
            ysat = (x > 32767) ? 16'sh7fff : ((x < -32768) ? 16'sh8000 : x[15:0]);
        end
    endfunction

    function signed [15:0] esat;                    // d - y, saturate to 16 bits
        input signed [15:0] d;
        input signed [15:0] y;
        reg   signed [16:0] x;
        begin
            x = d - y;
            esat = (x > 32767) ? 16'sh7fff : ((x < -32768) ? 16'sh8000 : x[15:0]);
        end
    endfunction

    // update shift amount for mu = 2^-p: exact e*u has 2*FR fractional bits, mu adds p, the accumulator keeps FA
    wire signed [7:0] shu = 2 * FR + $signed({4'd0, p_in}) - FA;

    integer k;
    reg signed [DW-1:0]    x40;
    reg signed [QW-1:0]    ta, tf;
    reg signed [SW-1:0]    ua, uf;
    reg signed [B_ACC+1:0] s2;
    reg        [4:0]       c_nz, c_zs;

    always @(posedge clk) begin
        if (rst) begin
            stg     <= 9'd0;
            valid   <= 1'b0;
            stalls  <= 32'd0;
            updates <= 32'd0;
            for (k = 0; k < L; k = k + 1) begin
                acc[k] <= 0;
                wf[k]  <= 0;
                u[k]   <= 0;
            end
        end else begin
            stg   <= {stg[7:0], en};
            valid <= stg[8];

            // k: input latch, delay line, coefficients, R2 bank
            if (en) begin
                d_l  <= d_in;
                uf_l <= use_frozen;
                shr  <= (shu > 0) ? shu[5:0] : 6'd0;
                shl  <= (shu < 0) ? -shu[5:0] : 6'd0;
                hr   <= (RND && shu > 0) ? (34'sd1 <<< (shu - 1)) : 34'sd0;
                u[0] <= r_in;
                for (k = 1; k < L; k = k + 1) u[k] <= u[k - 1];
                for (k = 0; k < L; k = k + 1) begin
                    wm[k] <= coef(acc[k]);
                    if (freeze_now) wf[k] <= coef(acc[k]);
                end
            end

            // k+1: products
            if (stg[0]) begin
                for (k = 0; k < L; k = k + 1) begin
                    pa[k] <= wm[k] * u[k];
                    pf[k] <= wf[k] * u[k];
                end
            end

            // k+2: partial sums
            if (stg[1]) begin
                for (k = 0; k < NG; k = k + 1) begin
                    qa[k] <= pa[4*k] + pa[4*k+1] + pa[4*k+2] + pa[4*k+3];
                    qf[k] <= pf[4*k] + pf[4*k+1] + pf[4*k+2] + pf[4*k+3];
                end
            end

            // k+3: full sums
            if (stg[2]) begin
                ua = 0; uf = 0;
                for (k = 0; k < NG; k = k + 1) begin
                    ta = qa[k]; tf = qf[k];
                    ua = ua + ta;
                    uf = uf + tf;
                end
                sa <= ua;
                sf <= uf;
            end

            // k+4: filter outputs
            if (stg[3]) begin
                ya_r <= ysat(sa);
                yf_r <= uf_l ? ysat(sf) : ysat(sa);
            end

            // k+5: errors (outputs)
            if (stg[4]) begin
                ya <= ya_r;
                yf <= yf_r;
                ea <= esat(d_l, ya_r);
                ef <= esat(d_l, yf_r);
            end

            // k+6: update products with the rounding constant (one DSP48E1 each: multiply + post-adder); nonzero flags
            if (stg[5]) begin
                for (k = 0; k < L; k = k + 1) begin
                    tr[k] <= ea * u[k] + hr;
                    nz[k] <= (ea != 0) && (u[k] != 0);
                end
            end

            // k+7: mu shift (arithmetic; floor after adding hr = round to nearest, ties up)
            if (stg[6]) begin
                for (k = 0; k < L; k = k + 1) begin
                    x40 = tr[k];
                    xs[k] <= (x40 >>> shr) <<< shl;
                end
            end

            // k+8: limit to B_ACC+1 bits, stall flags.
            // Limiting is exact: any update outside +-2^B_ACC saturates the accumulator in the same direction anyway.
            if (stg[7]) begin
                for (k = 0; k < L; k = k + 1) begin
                    dl[k] <= (xs[k] > DHI) ? DHI[B_ACC:0] : ((xs[k] < DLO) ? DLO[B_ACC:0] : xs[k][B_ACC:0]);
                    zs[k] <= nz[k] && (xs[k] == 0);
                end
            end

            // k+9: accumulator update and counters
            if (stg[8]) begin
                c_nz = 0; c_zs = 0;
                for (k = 0; k < L; k = k + 1) begin
                    s2 = acc[k] + dl[k];
                    acc[k] <= (s2 > AHI) ? AHI[B_ACC-1:0] : ((s2 < ALO) ? ALO[B_ACC-1:0] : s2[B_ACC-1:0]);
                    c_nz = c_nz + nz[k];
                    c_zs = c_zs + zs[k];
                end
                updates <= updates + c_nz;
                stalls  <= stalls + c_zs;
            end
        end
    end

    // synthesis translate_off
    // cycle budget (V10): a new symbol must not start before the previous update is in the accumulators
    always @(posedge clk) begin
        if (!rst && en && busy) $display("ERROR lms_rx_syn: en while busy at time %0t (symbols closer than 10 clocks)", $time);
    end
    initial begin
        if (B_ACC < B_MUL) $display("ERROR lms_rx_syn: B_ACC < B_MUL is not supported");
        if (L % 4 != 0)    $display("ERROR lms_rx_syn: L must be a multiple of 4");
        if (B_MUL < 3)     $display("ERROR lms_rx_syn: B_MUL must be at least 3");
    end
    // synthesis translate_on
endmodule
