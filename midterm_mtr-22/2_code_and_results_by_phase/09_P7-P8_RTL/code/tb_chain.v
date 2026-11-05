// tb_chain.v -- testbench for rx_chain.  Reads {DIR}/seeds.hex and {DIR}/bits.hex (one 0/1 per line, all NSYM bits);
// writes one line per symbol (r_q d_q ya yf ea ef) and a final COUNTERS line to {DIR}/out_chain.txt
`timescale 1ns/1ps
module tb_chain;
    parameter NSYM   = 6000;
    parameter NT     = 1500;
    parameter B_MUL  = 12;
    parameter B_ACC  = 16;
    parameter P      = 8;
    parameter RND    = 1;
    parameter C_LO   = 40;
    parameter C_HI   = 116;
    parameter SVAL   = 20;
    parameter SIGQ   = 13100;
    parameter STATIC = 0;
    parameter DIR    = "vec";

    reg clk = 0, rst = 1, load = 0;
    reg  [12*36-1:0] seeds;
    reg [35:0] seed_mem [0:11];
    reg bits_mem [0:NSYM];
    wire [31:0] sym_idx, n_eval, err1, err2, err3, stalls, updates;
    wire sym_done;
    wire signed [15:0] o_r, o_d, o_ya, o_yf, o_ea, o_ef;
    wire [63:0] sse2, sse3;
    wire bit_in = (sym_idx < NSYM) ? bits_mem[sym_idx] : 1'b0;

    rx_chain #(.N_T(NT), .B_MUL(B_MUL), .B_ACC(B_ACC), .P(P), .RND(RND)) dut (
        .clk(clk), .rst(rst), .load(load), .seeds(seeds), .bit_in(bit_in), .static_mode(STATIC != 0),
        .c_lo(C_LO[6:0]), .c_hi(C_HI[6:0]), .S(SVAL[15:0]), .sigma_q(SIGQ[16:0]),
        .sym_idx(sym_idx), .sym_done(sym_done), .o_r(o_r), .o_d(o_d), .o_ya(o_ya), .o_yf(o_yf), .o_ea(o_ea), .o_ef(o_ef),
        .n_eval(n_eval), .err1(err1), .err2(err2), .err3(err3), .sse2(sse2), .sse3(sse3), .stalls(stalls), .updates(updates));
    always #5 clk = ~clk;

    integer fo, i;
    always @(posedge clk) if (sym_done) $fdisplay(fo, "%0d %0d %0d %0d %0d %0d", o_r, o_d, o_ya, o_yf, o_ea, o_ef);

    initial begin
        $readmemh({DIR, "/seeds.hex"}, seed_mem);
        $readmemh({DIR, "/bits.hex"}, bits_mem);
        for (i = 0; i < 12; i = i + 1) seeds[36*i +: 36] = seed_mem[i];
        fo = $fopen({DIR, "/out_chain.txt"}, "w");
        repeat (3) @(posedge clk);
        rst <= 0;
        @(posedge clk); load <= 1;
        @(posedge clk); load <= 0;
        wait (sym_idx == NSYM);
        repeat (5) @(posedge clk);
        $fdisplay(fo, "COUNTERS %0d %0d %0d %0d %0d %0d %0d %0d", n_eval, err1, err2, err3, sse2, sse3, stalls, updates);
        $fclose(fo);
        $display("tb_chain done");
        $finish;
    end
endmodule
