// top_boolean.v -- top level for the Real Digital Boolean Board (XC7S50), 100 MHz.
// Two ways to run the experiment on the same hardware (exp_core):
//   * host mode: the PC sends a complete configuration over the USB-UART (host_if.v) and receives all counters at the end
//     of the run; used for the L5 measurements, which are compared with the L2 model count for count;
//   * demo mode (after power-up and after BTN0): configuration from the switches, training (N_T = 30000) and then continuous
//     tracking; error counts of the receivers per window of 2^20 tracking symbols (about 0.17 s) on the displays.
// Switches (demo mode):
//   SW[2:0]  variation rate S: 0 static, 1: 5000, 2: 1000, 3: 224, 4: 112, 5: 28, 6: 5, 7: 1
//   SW[5:3]  mu = 2^-p, p = 5 + SW[5:3] (value 7 gives p = 11 as well)
//   SW[7:6]  noise: Eb/N0 = 8, 10, 12, 14 dB
//   SW[8]    channel: 0 primary (c 40..116, a = 0.31..0.91), 1 control (c 26..77, a = 0.20..0.60)  -- a change retrains
//   SW[9]    display 1 shows R1 instead of R2
// Displays: display 1 = R2 (or R1) errors per window, display 0 = R3 errors per window (errors per 2^20 bits ~ BER in ppm).
// Buttons:  BTN0 retrain with the switch settings (and leave host mode); BTN1 clear the counters; BTN3 reset.
// LEDs: LED[9:0] = SW[9:0]; LED13 host mode; LED14 tracking; LED15 training.
// RGB0: blue = training, green = tracking.   RGB1 (R3 errors per window): green < 100, yellow 100..999, red >= 1000.
// Level L3 (L4/L5 after implementation).  Responsible member: Bhavyam Shankar (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module top_boolean #(
    parameter B_MUL        = 12,
    parameter B_ACC        = 16,
    parameter RND          = 1,
    parameter CLKS_PER_BIT = 868,       // 115200 baud at 100 MHz
    parameter DEB_N        = 20,        // button debounce, 2^DEB_N clocks
    parameter WIN_LOG2     = 20,        // demo window, 2^WIN_LOG2 tracking symbols
    parameter DEMO_NT      = 30000
)(
    input  wire        clk,
    input  wire [15:0] sw,
    input  wire [3:0]  btn,
    output wire [15:0] led,
    output wire [2:0]  RGB0,
    output wire [2:0]  RGB1,
    output wire [3:0]  D0_AN,
    output wire [7:0]  D0_SEG,
    output wire [3:0]  D1_AN,
    output wire [7:0]  D1_SEG,
    input  wire        UART_rxd,       // into the FPGA
    output wire        UART_txd        // out of the FPGA
);
    // ---- reset: power-on and BTN3 ----
    wire b0, b0_rise, b1_rise, b3;
    debounce #(.N(DEB_N)) u_b0 (.clk(clk), .in(btn[0]), .out(b0),  .rise(b0_rise));
    debounce #(.N(DEB_N)) u_b1 (.clk(clk), .in(btn[1]), .out(),    .rise(b1_rise));
    debounce #(.N(DEB_N)) u_b3 (.clk(clk), .in(btn[3]), .out(b3),  .rise());
    reg [7:0] por = 8'd0;
    reg       rst = 1'b1;
    always @(posedge clk) begin
        if (b3) por <= 8'd0;
        else if (!por[7]) por <= por + 8'd1;
        rst <= !por[7];
    end

    // ---- switches (two-flop synchroniser) ----
    reg [15:0] sw_s1, sw_s;
    always @(posedge clk) begin sw_s1 <= sw; sw_s <= sw_s1; end

    // ---- demo configuration ----
    reg [15:0] d_S;
    reg        d_static;
    always @(*) begin
        d_static = 1'b0;
        case (sw_s[2:0])
            3'd0: begin d_S = 16'd1; d_static = 1'b1; end
            3'd1: d_S = 16'd5000;
            3'd2: d_S = 16'd1000;
            3'd3: d_S = 16'd224;
            3'd4: d_S = 16'd112;
            3'd5: d_S = 16'd28;
            3'd6: d_S = 16'd5;
            default: d_S = 16'd1;
        endcase
    end
    wire [3:0]  d_p    = (sw_s[5:3] == 3'd7) ? 4'd11 : 4'd5 + {1'b0, sw_s[5:3]};
    reg  [16:0] d_sig;
    always @(*) case (sw_s[7:6])                                  // fxp_front.sigma_q_from_ebn0
        2'd0: d_sig = 17'd18449;                                  //  8 dB
        2'd1: d_sig = 17'd14654;                                  // 10 dB
        2'd2: d_sig = 17'd11640;                                  // 12 dB
        default: d_sig = 17'd9246;                                // 14 dB
    endcase
    wire [6:0] d_clo = sw_s[8] ? 7'd26 : 7'd40;
    wire [6:0] d_chi = sw_s[8] ? 7'd77 : 7'd116;
    // noise start values: fxp_front.lfsr_start_values(2000 + 500000) (final seed 2000)
    localparam [12*36-1:0] DEMO_SEEDS = {36'h49c47ad49, 36'h0b970298d, 36'h0263e9a52, 36'h01cc69cd3, 36'h003f4e20c, 36'h001fe8487,
                                         36'h00001f639, 36'h0001a9271, 36'h000080b96, 36'h000026a95, 36'h000012032, 36'h000008e85};

    // ---- host interface ----
    wire [3:0]  h_p;   wire [15:0] h_S;  wire [6:0] h_clo, h_chi;  wire h_static;  wire [16:0] h_sig;
    wire [31:0] h_nt, h_ntot;  wire [30:0] h_pay;  wire [12*36-1:0] h_seeds;
    wire h_start, h_stop, host_mode;
    wire running, done, tracking, sym_done;
    wire [31:0] sym_idx, n_eval, err1, err2, err3, stalls, updates;
    wire [63:0] sse2, sse3;
    host_if #(.CLKS_PER_BIT(CLKS_PER_BIT), .B_MUL(B_MUL), .B_ACC(B_ACC), .RND(RND)) u_host (
        .clk(clk), .rst(rst), .rxd(UART_rxd), .txd(UART_txd),
        .p_in(h_p), .S(h_S), .c_lo(h_clo), .c_hi(h_chi), .static_mode(h_static), .sigma_q(h_sig), .n_t(h_nt), .n_total(h_ntot),
        .pay_seed(h_pay), .seeds(h_seeds), .start(h_start), .stop(h_stop), .host_mode(host_mode), .clear_host(b0_rise),
        .running(running), .done(done), .tracking(tracking), .sym_idx(sym_idx), .n_eval(n_eval), .err1(err1), .err2(err2),
        .err3(err3), .sse2(sse2), .sse3(sse3), .stalls(stalls), .updates(updates));

    // ---- demo start: after reset, BTN0, or a change of the channel switch ----
    reg rst_d = 1'b1, ch_d = 1'b0;
    always @(posedge clk) begin rst_d <= rst; ch_d <= sw_s[8]; end
    wire d_start = !host_mode && ((rst_d && !rst) || (ch_d != sw_s[8])) || b0_rise;

    // ---- experiment ----
    exp_core #(.B_MUL(B_MUL), .B_ACC(B_ACC), .RND(RND)) u_exp (
        .clk(clk), .rst(rst), .start(h_start | d_start), .stop(h_stop), .clr_cnt(b1_rise),
        .p_in(host_mode ? h_p : d_p), .S(host_mode ? h_S : d_S), .c_lo(host_mode ? h_clo : d_clo), .c_hi(host_mode ? h_chi : d_chi),
        .static_mode(host_mode ? h_static : d_static), .sigma_q(host_mode ? h_sig : d_sig),
        .n_t(host_mode ? h_nt : DEMO_NT), .n_total(host_mode ? h_ntot : 32'd0),
        .pay_seed(host_mode ? h_pay : 31'd12345), .seeds(host_mode ? h_seeds : DEMO_SEEDS),
        .running(running), .done(done), .tracking(tracking), .sym_done(sym_done), .sym_idx(sym_idx),
        .n_eval(n_eval), .err1(err1), .err2(err2), .err3(err3), .sse2(sse2), .sse3(sse3), .stalls(stalls), .updates(updates));

    // ---- error counts per window (demo display) ----
    reg [31:0] p1, p2, p3;
    reg [13:0] w1, w2, w3;
    always @(posedge clk) begin
        if (rst || b1_rise || !tracking) begin
            p1 <= err1; p2 <= err2; p3 <= err3;
        end else if (sym_done && n_eval[WIN_LOG2-1:0] == 0) begin
            w1 <= (err1 - p1 > 9999) ? 14'd9999 : err1 - p1;
            w2 <= (err2 - p2 > 9999) ? 14'd9999 : err2 - p2;
            w3 <= (err3 - p3 > 9999) ? 14'd9999 : err3 - p3;
            p1 <= err1; p2 <= err2; p3 <= err3;
        end
    end

    sevenseg2 u_seg (.clk(clk), .val0(w3), .val1(sw_s[9] ? w1 : w2), .an0(D0_AN), .seg0(D0_SEG), .an1(D1_AN), .seg1(D1_SEG));

    // ---- LEDs (RGB dimmed to 1/16 duty) ----
    reg [3:0] pwm = 4'd0;
    always @(posedge clk) pwm <= pwm + 4'd1;
    wire dim = (pwm == 4'd0);
    wire training = running && !tracking;
    assign led  = {training, tracking, host_mode, 3'b000, sw_s[9:0]};
    assign RGB0 = {training & dim, tracking & dim, 1'b0};                         // {B, G, R}
    wire r3_hi  = (w3 >= 14'd1000), r3_mid = (w3 >= 14'd100);
    assign RGB1 = {1'b0, tracking & !r3_hi & dim, tracking & r3_mid & dim};       // green / yellow (R+G) / red
endmodule
