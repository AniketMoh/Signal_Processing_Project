// chan_front.v -- integer front end: channel [1, a[n], h2] + noise, rounding to s16.12, and the desired symbol.  Level L3.
// Defined in fxp_front.py (L2 front end, integer version).  All values in units of 2^-16 until the final rounding:
//     r_hi = 65536*x[n] + 512*c[n]*x[n-1] + H2Q*x[n-2] + noise16,       a = c/128 -> a*65536 = 512*c (exact)
//     noise16 = round( sigma_q * noise_int / 65536 )                     sigma_q = round(sigma*65536), noise_int from lfsr_noise
//     r_q = saturate16( round( r_hi / 16 ) )                             (s16.12, ties up)
//     d_q = 4096 * x[n-2]                                                (Delta = 2, zero before the start)
// x is +1/-1 (bit 1 -> +1).  H2Q = round(0.1*65536) = 6554 (h2 = 0.100006).
module chan_front #(
    parameter H2Q = 6554
)(
    input  wire               clk,
    input  wire               rst,
    input  wire               en,          // one pulse per symbol
    input  wire               x_bit,       // transmitted bit of this symbol
    input  wire        [6:0]  c,           // channel counter of this symbol
    input  wire signed [19:0] noise,       // noise_int (units 2^-16)
    input  wire        [16:0] sigma_q,     // sigma * 65536
    output reg  signed [15:0] r_q,
    output reg  signed [15:0] d_q
);
    reg signed [1:0] x1, x2;               // x[n-1], x[n-2]  in {-1, 0, +1}
    reg signed [63:0] x0, n16, rhi, rr;
    always @(posedge clk) begin
        if (rst) begin
            x1 <= 2'sd0; x2 <= 2'sd0; r_q <= 16'sd0; d_q <= 16'sd0;
        end else if (en) begin
            x0  = x_bit ? 64'sd1 : -64'sd1;
            n16 = ($signed({47'd0, sigma_q}) * $signed({{44{noise[19]}}, noise}) + 64'sd32768) >>> 16;
            rhi = 64'sd65536 * x0 + 64'sd512 * $signed({57'd0, c}) * $signed({{62{x1[1]}}, x1})
                + H2Q * $signed({{62{x2[1]}}, x2}) + n16;
            rr  = (rhi + 64'sd8) >>> 4;
            r_q <= (rr > 64'sd32767) ? 16'sd32767 : ((rr < -64'sd32768) ? -16'sd32768 : rr[15:0]);
            d_q <= 16'sd4096 * x2;
            x2 <= x1;
            x1 <= x0[1:0];
        end
    end
endmodule
