// exp_core.v -- one experiment on the board: rx_chain_syn + on-chip payload LFSR + run control.
//   start (pulse): load the noise seeds and the payload seed, clear the chain (training starts again from w = 0) and run.
//   The run stops after n_total symbols (n_total = 0: run until 'stop' or the next 'start').  done stays 1 until the next start.
//   The configuration inputs are used live (mu, S, sigma can change during a run; the seeds are read only at start).
// Level L3.  Responsible member: Aniket Mohapatra (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module exp_core #(
    parameter B_MUL = 12,
    parameter B_ACC = 16,
    parameter RND   = 1
)(
    input  wire              clk,
    input  wire              rst,
    input  wire              start,
    input  wire              stop,
    input  wire              clr_cnt,
    input  wire [3:0]        p_in,
    input  wire [15:0]       S,
    input  wire [6:0]        c_lo,
    input  wire [6:0]        c_hi,
    input  wire              static_mode,
    input  wire [16:0]       sigma_q,
    input  wire [31:0]       n_t,
    input  wire [31:0]       n_total,
    input  wire [30:0]       pay_seed,
    input  wire [12*36-1:0]  seeds,
    output reg               running,
    output reg               done,
    output wire              tracking,      // running and past the training part
    output wire              sym_done,
    output wire [31:0]       sym_idx,
    output wire [31:0]       n_eval, err1, err2, err3,
    output wire [63:0]       sse2, sse3,
    output wire [31:0]       stalls, updates
);
    reg load;
    wire run, front_en, pay_bit;

    payload_lfsr u_pay (.clk(clk), .load(load), .seed(pay_seed), .en(front_en && run), .bit_out(pay_bit));

    rx_chain_syn #(.B_MUL(B_MUL), .B_ACC(B_ACC), .RND(RND)) u_chain (
        .clk(clk), .rst(rst), .load(load), .seeds(seeds), .run_en(running), .clr_cnt(clr_cnt), .bit_in(pay_bit),
        .static_mode(static_mode), .c_lo(c_lo), .c_hi(c_hi), .S(S), .sigma_q(sigma_q), .p_in(p_in), .n_t(n_t),
        .sym_idx(sym_idx), .sym_done(sym_done), .front_en_o(front_en), .run(run),
        .o_r(), .o_d(), .o_ya(), .o_yf(), .o_ea(), .o_ef(),
        .n_eval(n_eval), .err1(err1), .err2(err2), .err3(err3), .sse2(sse2), .sse3(sse3), .stalls(stalls), .updates(updates));

    assign tracking = running && run;

    // The last symbol finishes 14 clocks after its noise word; running falls on the clock after sym_done, before the next
    // noise word (16 clocks) is complete, so no partial symbol is started.
    reg go;
    always @(posedge clk) begin
        load <= 1'b0;
        go   <= 1'b0;
        if (rst) begin
            running <= 1'b0; done <= 1'b0;
        end else if (start) begin
            load <= 1'b1; go <= 1'b1; running <= 1'b0; done <= 1'b0;
        end else if (go) begin
            running <= 1'b1;
        end else if (running && (stop || (sym_done && n_total != 0 && sym_idx == n_total))) begin
            running <= 1'b0; done <= 1'b1;
        end
    end
endmodule
