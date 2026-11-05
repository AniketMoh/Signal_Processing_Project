// rx_chain.v -- complete transmit-channel-receive chain of the project (without UART): PRBS training, payload bit, variation controller,
// FPGA-style noise, integer front end, R1 direct detector, R2 frozen LMS, R3 adaptive LMS, error and MSE counters.  Level L3.
// One symbol per noise sample (every 16 clocks).  Counters run for symbols n >= N_T.
//   R1: bit decision (r_q >= 0) against the bit of the same symbol.   R2, R3: (y >= 0) against the bit two symbols earlier (Delta = 2).
//   MSE sums are integers in units of 2^-24 (sum of e*e with e in s16.12).
module rx_chain #(
    parameter N_T   = 1500,
    parameter B_MUL = 12,
    parameter B_ACC = 16,
    parameter P     = 8,
    parameter RND   = 1
)(
    input  wire              clk,
    input  wire              rst,
    input  wire              load,          // load the noise LFSR start values and clear the counters/state of the chain
    input  wire [12*36-1:0]  seeds,
    input  wire              bit_in,        // payload bit for symbol sym_idx (used for sym_idx >= N_T)
    input  wire              static_mode,
    input  wire [6:0]        c_lo,
    input  wire [6:0]        c_hi,
    input  wire [15:0]       S,
    input  wire [16:0]       sigma_q,
    output reg  [31:0]       sym_idx,       // index of the symbol being processed / next symbol
    output reg               sym_done,      // one pulse when a symbol is finished
    output wire signed [15:0] o_r, o_d, o_ya, o_yf, o_ea, o_ef,
    output reg  [31:0]       n_eval, err1, err2, err3,
    output reg  [63:0]       sse2, sse3,    // sums of e^2 for R2 and R3
    output wire [31:0]       stalls, updates
);
    // ---- noise ----
    wire signed [19:0] noise;
    wire               nvalid;
    lfsr_noise u_noise (.clk(clk), .rst(rst), .load(load), .seeds(seeds), .en(1'b1), .noise(noise), .valid(nvalid));

    // ---- control of one symbol: nvalid -> front_en (clock 1) -> rx_en (clock 2) -> rx valid (clock 3) -> counters ----
    reg front_en, rx_en;
    reg signed [19:0] noise_l;
    wire run = (sym_idx >= N_T);

    wire prbs_bit;
    prbs15 u_prbs (.clk(clk), .rst(rst | load), .en(front_en && !run), .bit_out(prbs_bit));
    wire x_bit = run ? bit_in : prbs_bit;

    wire [6:0] c;
    var_ctrl u_var (.clk(clk), .rst(rst | load), .en(front_en), .run(run), .static_mode(static_mode), .c_lo(c_lo), .c_hi(c_hi), .S(S), .c(c));

    wire signed [15:0] r_q, d_q;
    chan_front u_front (.clk(clk), .rst(rst | load), .en(front_en), .x_bit(x_bit), .c(c), .noise(noise_l), .sigma_q(sigma_q), .r_q(r_q), .d_q(d_q));

    wire signed [15:0] ya, yf, ea, ef;
    wire signed [31:0] pef = ef * ef;      // squares are non-negative
    wire signed [31:0] pea = ea * ea;
    wire rx_valid;
    lms_rx #(.L(16), .B_MUL(B_MUL), .B_ACC(B_ACC), .P(P), .RND(RND)) u_rx (
        .clk(clk), .rst(rst | load), .en(rx_en), .r_in(r_q), .d_in(d_q),
        .freeze_now(sym_idx == N_T), .use_frozen(run),
        .ya(ya), .yf(yf), .ea(ea), .ef(ef), .valid(rx_valid), .stalls(stalls), .updates(updates));

    assign o_r = r_q; assign o_d = d_q; assign o_ya = ya; assign o_yf = yf; assign o_ea = ea; assign o_ef = ef;

    // bit history for the decisions
    reg hist1, hist2, cur0, cur2;
    always @(posedge clk) begin
        if (rst | load) begin
            hist1 <= 1'b0; hist2 <= 1'b0; cur0 <= 1'b0; cur2 <= 1'b0;
        end else if (front_en) begin
            cur0  <= x_bit;
            cur2  <= hist2;
            hist2 <= hist1;
            hist1 <= x_bit;
        end
    end

    always @(posedge clk) begin
        front_en <= 1'b0; rx_en <= 1'b0; sym_done <= 1'b0;
        if (rst | load) begin
            sym_idx <= 32'd0; n_eval <= 32'd0; err1 <= 32'd0; err2 <= 32'd0; err3 <= 32'd0; sse2 <= 64'd0; sse3 <= 64'd0;
        end else begin
            if (nvalid) begin
                noise_l  <= noise;
                front_en <= 1'b1;
            end
            if (front_en) rx_en <= 1'b1;
            if (rx_valid) begin
                if (run) begin
                    n_eval <= n_eval + 32'd1;
                    if ((r_q >= 0) != cur0) err1 <= err1 + 32'd1;
                    if ((yf  >= 0) != cur2) err2 <= err2 + 32'd1;
                    if ((ya  >= 0) != cur2) err3 <= err3 + 32'd1;
                    sse2 <= sse2 + {32'd0, pef};
                    sse3 <= sse3 + {32'd0, pea};
                end
                sym_idx  <= sym_idx + 32'd1;
                sym_done <= 1'b1;
            end
        end
    end
endmodule
