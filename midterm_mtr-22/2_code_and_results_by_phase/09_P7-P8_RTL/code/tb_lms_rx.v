// tb_lms_rx.v -- feeds r.txt and d.txt (one integer per line, s16.12) to lms_rx and writes ya yf ea ef per symbol to out_rtl.txt
`timescale 1ns/1ps
module tb_lms_rx;
    parameter NSYM  = 4000;
    parameter NT    = 1500;
    parameter B_MUL = 12;
    parameter B_ACC = 16;
    parameter P     = 8;
    parameter RND   = 1;
    parameter DIR   = "vec";

    reg clk = 0, rst = 1, en = 0, freeze_now = 0, use_frozen = 0;
    reg signed [15:0] r_in = 0, d_in = 0;
    wire signed [15:0] ya, yf, ea, ef;
    wire valid;
    wire [31:0] stalls, updates;

    lms_rx #(.L(16), .B_MUL(B_MUL), .B_ACC(B_ACC), .P(P), .RND(RND)) dut (
        .clk(clk), .rst(rst), .en(en), .r_in(r_in), .d_in(d_in), .freeze_now(freeze_now), .use_frozen(use_frozen),
        .ya(ya), .yf(yf), .ea(ea), .ef(ef), .valid(valid), .stalls(stalls), .updates(updates));
    always #5 clk = ~clk;

    integer fr, fd, fo, n, rv, dv, st;
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
            @(posedge clk);                         // outputs of this symbol are valid now
            #1;
            $fdisplay(fo, "%0d %0d %0d %0d", ya, yf, ea, ef);
        end
        $fdisplay(fo, "COUNTERS %0d %0d", stalls, updates);
        $fclose(fo);
        $display("tb_lms_rx done");
        $finish;
    end
endmodule
