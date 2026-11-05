// chan_front_syn.v -- integer front end: channel [1, a[n], h2] + noise, rounding to s16.12, desired symbol.  Synthesisable
// version of chan_front.v (09_P7-P8_RTL), same arithmetic (fxp_front.front_end_int, level L2):
//     r_hi = 65536*x[n] + 512*c[n]*x[n-1] + H2Q*x[n-2] + noise16          a = c/128 -> a*65536 = 512*c (exact)
//     noise16 = round( sigma_q * noise_int / 65536 )                       (ties up)
//     r_q = saturate16( round( r_hi / 16 ) )                               (s16.12, ties up)
//     d_q = 4096 * x[n-2]                                                  (Delta = 2, zero before the start)
// Differences: real widths (the sigma*noise product is 17 x 20 bits, one DSP48E1) and two clocks per symbol:
//     edge k (en):   latch bit and counter, sigma*noise product, shift the symbol history, d_q
//     edge k+1:      sum, round, saturate -> r_q; valid = 1 during the following clock
// Level L3.  Responsible member: Aniket Mohapatra (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module chan_front_syn #(
    parameter H2Q = 6554
)(
    input  wire               clk,
    input  wire               rst,
    input  wire               en,          // one pulse per symbol
    input  wire               x_bit,       // transmitted bit of this symbol
    input  wire        [6:0]  c,           // channel counter of this symbol
    input  wire signed [19:0] noise,       // noise_int (units 2^-16), stable during en
    input  wire        [16:0] sigma_q,     // sigma * 65536
    output reg  signed [15:0] r_q,
    output reg  signed [15:0] d_q,
    output reg                valid
);
    reg signed [1:0]  x0, x1, x2;          // x[n], x[n-1], x[n-2] in {-1, 0, +1}; x1/x2 below are for the latched symbol
    reg signed [1:0]  xa, xb;              // x[n-1], x[n-2] of the symbol being finished
    reg        [6:0]  c_l;
    reg               st1;
    (* use_dsp = "yes" *) reg signed [37:0] prod;

    reg signed [23:0] n16, cx, rhi, rr;
    always @(posedge clk) begin
        if (rst) begin
            x1 <= 2'sd0; x2 <= 2'sd0; r_q <= 16'sd0; d_q <= 16'sd0; st1 <= 1'b0; valid <= 1'b0;
        end else begin
            st1   <= en;
            valid <= st1;
            if (en) begin
                x0   <= x_bit ? 2'sd1 : -2'sd1;
                xa   <= x1;
                xb   <= x2;
                c_l  <= c;
                prod <= $signed({1'b0, sigma_q}) * noise;
                d_q  <= (x2 == 2'sd1) ? 16'sd4096 : ((x2 == -2'sd1) ? -16'sd4096 : 16'sd0);
                x2   <= x1;
                x1   <= x_bit ? 2'sd1 : -2'sd1;
            end
            if (st1) begin
                n16 = (prod + 38'sd32768) >>> 16;
                cx  = $signed({8'd0, c_l, 9'd0});                               // 512*c
                rhi = (x0 == 2'sd1 ? 24'sd65536 : -24'sd65536)
                    + (xa == 2'sd1 ? cx : (xa == -2'sd1 ? -cx : 24'sd0))
                    + (xb == 2'sd1 ? H2Q : (xb == -2'sd1 ? -H2Q : 0))
                    + n16;
                rr  = (rhi + 24'sd8) >>> 4;
                r_q <= (rr > 24'sd32767) ? 16'sh7fff : ((rr < -24'sd32768) ? 16'sh8000 : rr[15:0]);
            end
        end
    end
endmodule
