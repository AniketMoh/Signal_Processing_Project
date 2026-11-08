// rx_chain_syn.v -- complete transmit-channel-receive chain (no UART), synthesisable version of rx_chain.v (09_P7-P8_RTL):
// PRBS training, payload bit, variation controller, 12-LFSR noise, integer front end, R1 direct detector, R2 frozen LMS,
// R3 adaptive LMS, error and squared-error counters.  Same symbol rule and counter definitions as rx_chain.v:
//   one symbol per noise sample (every 16 clocks while run_en = 1); counters run for symbols n >= N_T;
//   R1: (r_q >= 0) against the bit of the same symbol;  R2, R3: (y >= 0) against the bit two symbols earlier (Delta = 2);
//   sse2, sse3 = sum of e^2 in units of 2^-24.
// Differences from rx_chain.v: lms_rx_syn / chan_front_syn / var_ctrl_syn; mu (p_in) and N_T are inputs; run_en gates the
// noise generator (symbols stop at a symbol boundary when run_en falls after sym_done); clr_cnt clears only the counters.
// Timing of one symbol (clock edges after the noise word is complete): noise latched -> front end (2) -> LMS (10) -> counters;
// 14 of the 16 clocks, so a symbol is finished before the next noise word arrives.
// Level L3.  Responsible member: Aniket Mohapatra (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module rx_chain_syn #(
    parameter B_MUL = 12,
    parameter B_ACC = 16,
    parameter RND   = 1
)(
    input  wire              clk,
    input  wire              rst,
    input  wire              load,          // load the noise LFSR start values and clear the state and counters of the chain
    input  wire [12*36-1:0]  seeds,
    input  wire              run_en,        // 1: produce symbols
    input  wire              clr_cnt,       // clear the error / MSE counters only
    input  wire              bit_in,        // payload bit for symbol sym_idx (used for sym_idx >= n_t)
    input  wire              static_mode,
    input  wire [6:0]        c_lo,
    input  wire [6:0]        c_hi,
    input  wire [15:0]       S,
    input  wire [16:0]       sigma_q,
    input  wire [3:0]        p_in,          // mu = 2^-p_in
    input  wire [31:0]       n_t,           // training length N_T
    output reg  [31:0]       sym_idx,       // index of the symbol being processed / next symbol
    output reg               sym_done,      // one pulse when a symbol is finished
    output wire              front_en_o,    // one pulse when a new symbol enters the front end (payload bit consumed)
    output wire              run,           // sym_idx >= n_t (tracking part)
    output wire signed [15:0] o_r, o_d, o_ya, o_yf, o_ea, o_ef,
    output reg  [31:0]       n_eval, err1, err2, err3,
    output reg  [63:0]       sse2, sse3,
    output wire [31:0]       stalls, updates,
    // decisions of one tracking symbol (n >= N_T), valid together with dec_valid:
    //   dec1 = R1 decision of bit n, dec2 / dec3 = R2 / R3 decisions of bit n-2 (Delta = 2)
    output wire              dec_valid,
    output wire              dec1, dec2, dec3
);
    // ---- noise (teammates' lfsr_noise.v, synthesisable as written) ----
    wire signed [19:0] noise;
    wire               nvalid;
    lfsr_noise u_noise (.clk(clk), .rst(rst), .load(load), .seeds(seeds), .en(run_en), .noise(noise), .valid(nvalid));

    reg front_en;
    reg signed [19:0] noise_l;
    assign run = (sym_idx >= n_t);
    assign front_en_o = front_en;

    wire prbs_bit;
    prbs15 u_prbs (.clk(clk), .rst(rst | load), .en(front_en && !run), .bit_out(prbs_bit));
    wire x_bit = run ? bit_in : prbs_bit;

    wire [6:0] c;
    var_ctrl_syn u_var (.clk(clk), .rst(rst | load), .en(front_en), .run(run), .static_mode(static_mode),
                        .c_lo(c_lo), .c_hi(c_hi), .S(S), .c(c));

    wire signed [15:0] r_q, d_q;
    wire fvalid;
    chan_front_syn u_front (.clk(clk), .rst(rst | load), .en(front_en), .x_bit(x_bit), .c(c), .noise(noise_l),
                            .sigma_q(sigma_q), .r_q(r_q), .d_q(d_q), .valid(fvalid));

    wire signed [15:0] ya, yf, ea, ef;
    wire rx_valid, rx_busy;
    lms_rx_syn #(.L(16), .B_MUL(B_MUL), .B_ACC(B_ACC), .RND(RND)) u_rx (
        .clk(clk), .rst(rst | load), .en(fvalid), .r_in(r_q), .d_in(d_q), .p_in(p_in),
        .freeze_now(sym_idx == n_t), .use_frozen(run),
        .ya(ya), .yf(yf), .ea(ea), .ef(ef), .valid(rx_valid), .busy(rx_busy), .stalls(stalls), .updates(updates));

    assign o_r = r_q; assign o_d = d_q; assign o_ya = ya; assign o_yf = yf; assign o_ea = ea; assign o_ef = ef;

    // squared errors (one DSP48E1 each), registered while the LMS finishes
    (* use_dsp = "yes" *) reg [31:0] pef, pea;
    always @(posedge clk) begin
        pef <= ef * ef;
        pea <= ea * ea;
    end

    // bit history for the decisions, and the R1 decision of this symbol
    reg hist1, hist2, cur0, cur2, r1_bit;
    always @(posedge clk) begin
        if (rst | load) begin
            hist1 <= 1'b0; hist2 <= 1'b0; cur0 <= 1'b0; cur2 <= 1'b0; r1_bit <= 1'b0;
        end else begin
            if (front_en) begin
                cur0  <= x_bit;
                cur2  <= hist2;
                hist2 <= hist1;
                hist1 <= x_bit;
            end
            if (fvalid) r1_bit <= (r_q >= 0);
        end
    end

    always @(posedge clk) begin
        front_en <= 1'b0; sym_done <= 1'b0;
        if (rst | load) begin
            sym_idx <= 32'd0; n_eval <= 32'd0; err1 <= 32'd0; err2 <= 32'd0; err3 <= 32'd0; sse2 <= 64'd0; sse3 <= 64'd0;
        end else begin
            if (nvalid) begin
                noise_l  <= noise;
                front_en <= 1'b1;
            end
            if (clr_cnt) begin
                n_eval <= 32'd0; err1 <= 32'd0; err2 <= 32'd0; err3 <= 32'd0; sse2 <= 64'd0; sse3 <= 64'd0;
            end else if (rx_valid && run) begin
                n_eval <= n_eval + 32'd1;
                if (r1_bit    != cur0) err1 <= err1 + 32'd1;
                if ((yf >= 0) != cur2) err2 <= err2 + 32'd1;
                if ((ya >= 0) != cur2) err3 <= err3 + 32'd1;
                sse2 <= sse2 + {32'd0, pef};
                sse3 <= sse3 + {32'd0, pea};
            end
            if (rx_valid) begin
                sym_idx  <= sym_idx + 32'd1;
                sym_done <= 1'b1;
            end
        end
    end

    assign dec_valid = rx_valid && run;
    assign dec1 = r1_bit;
    assign dec2 = (yf >= 0);
    assign dec3 = (ya >= 0);

    // synthesis translate_off
    always @(posedge clk) if (!rst && fvalid && rx_busy) $display("ERROR rx_chain_syn: symbol overlap at %0t", $time);
    // synthesis translate_on
endmodule
