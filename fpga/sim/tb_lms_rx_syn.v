// tb_lms_rx_syn.v -- feeds r.txt and d.txt (one integer per line, s16.12) to lms_rx_syn, one symbol every SPACING clocks,
// and writes "ya yf ea ef" for every valid output to out_rtl.txt, then a final COUNTERS line.  Level L3.
// Responsible member: Pradeep Kumar (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.  Same file format as tb_lms_rx.v (09_P7-P8_RTL).
`timescale 1ns/1ps
module tb_lms_rx_syn;
    parameter NSYM    = 4000;
    parameter NT      = 1500;
    parameter B_MUL   = 12;
    parameter B_ACC   = 16;
    parameter P       = 8;
    parameter RND     = 1;
    parameter SPACING = 16;        // clocks between symbols (rx_chain gives 16; the minimum is 10)
    parameter DIR     = "vec";

    reg clk = 0, rst = 1, en = 0, freeze_now = 0, use_frozen = 0;
    reg signed [15:0] r_in = 0, d_in = 0;
    wire signed [15:0] ya, yf, ea, ef;
    wire valid, busy;
    wire [31:0] stalls, updates;

    lms_rx_syn #(.L(16), .B_MUL(B_MUL), .B_ACC(B_ACC), .RND(RND)) dut (
        .clk(clk), .rst(rst), .en(en), .r_in(r_in), .d_in(d_in), .p_in(P[3:0]),
        .freeze_now(freeze_now), .use_frozen(use_frozen),
        .ya(ya), .yf(yf), .ea(ea), .ef(ef), .valid(valid), .busy(busy), .stalls(stalls), .updates(updates));
    always #5 clk = ~clk;

    integer fr, fd, fo, n, rv, dv, st, nout = 0;
    always @(posedge clk) if (valid) begin
        $fdisplay(fo, "%0d %0d %0d %0d", ya, yf, ea, ef);
        nout = nout + 1;
    end

    initial begin
        fr = $fopen({DIR, "/r.txt"}, "r");
        fd = $fopen({DIR, "/d.txt"}, "r");
        fo = $fopen({DIR, "/out_rtl.txt"}, "w");
        repeat (3) @(posedge clk);
        rst <= 0;
        @(posedge clk);
        for (n = 0; n < NSYM; n = n + 1) begin
            st = $fscanf(fr, "%d", rv);
            st = $fscanf(fd, "%d", dv);
            r_in <= rv; d_in <= dv;
            use_frozen <= (n >= NT);
            freeze_now <= (n == NT);
            en <= 1;
            @(posedge clk);
            en <= 0; freeze_now <= 0;
            repeat (SPACING - 1) @(posedge clk);
        end
        repeat (12) @(posedge clk);
        $fdisplay(fo, "COUNTERS %0d %0d", stalls, updates);
        $fclose(fo);
        $display("tb_lms_rx_syn done, %0d outputs", nout);
        $finish;
    end
endmodule
