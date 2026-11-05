// tb_top.v -- top_boolean with a UART model on both lines.  Reads {DIR}/cmds.txt: groups "K W b0 b1 ... b(K-1)" (decimal):
// send the K bytes, then wait until W bytes in total have been received.  Every received byte goes to {DIR}/rx.txt.
// Fast settings for simulation: 16 clocks per UART bit, short debounce.  Level L3.
// Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
`timescale 1ns/1ps
module tb_top;
    parameter B_MUL = 12;
    parameter B_ACC = 16;
    parameter RND   = 1;
    parameter CPB   = 16;
    parameter DIR   = "vec";
    parameter MAXCLK = 50000000;

    reg clk = 0;
    always #5 clk = ~clk;
    reg  [15:0] sw = 16'h0000;
    reg  [3:0]  btn = 4'd0;
    reg         rxd = 1'b1;
    wire        txd;
    wire [15:0] led;
    wire [2:0]  rgb0, rgb1;
    wire [3:0]  an0, an1;
    wire [7:0]  seg0, seg1;

    top_boolean #(.B_MUL(B_MUL), .B_ACC(B_ACC), .RND(RND), .CLKS_PER_BIT(CPB), .DEB_N(4), .WIN_LOG2(8), .DEMO_NT(1500)) dut (
        .clk(clk), .sw(sw), .btn(btn), .led(led), .RGB0(rgb0), .RGB1(rgb1), .D0_AN(an0), .D0_SEG(seg0), .D1_AN(an1), .D1_SEG(seg1),
        .UART_rxd(rxd), .UART_txd(txd));

    // ---- receiver model (samples the middle of each bit) ----
    integer frx, nrx = 0, b;
    reg [7:0] rb;
    always begin
        @(negedge txd);
        repeat (CPB / 2) @(posedge clk);
        if (txd == 1'b0) begin
            for (b = 0; b < 8; b = b + 1) begin repeat (CPB) @(posedge clk); rb[b] = txd; end
            repeat (CPB) @(posedge clk);                       // stop bit
            if (txd !== 1'b1) $display("ERROR tb_top: framing error on txd");
            $fdisplay(frx, "%0d", rb);
            nrx = nrx + 1;
        end
    end

    task send_byte(input [7:0] v);
        integer j;
        begin
            rxd = 1'b0; repeat (CPB) @(posedge clk);
            for (j = 0; j < 8; j = j + 1) begin rxd = v[j]; repeat (CPB) @(posedge clk); end
            rxd = 1'b1; repeat (CPB) @(posedge clk);
        end
    endtask

    integer fc, st, k, w, i, v, nclk = 0;
    always @(posedge clk) begin
        nclk = nclk + 1;
        if (nclk == MAXCLK) begin $display("ERROR tb_top: timeout"); $fclose(frx); $finish; end
    end
    initial begin
        fc  = $fopen({DIR, "/cmds.txt"}, "r");
        frx = $fopen({DIR, "/rx.txt"}, "w");
        repeat (400) @(posedge clk);                           // reset and the automatic demo start
        while (!$feof(fc)) begin
            st = $fscanf(fc, "%d %d", k, w);
            if (st == 2) begin
                for (i = 0; i < k; i = i + 1) begin st = $fscanf(fc, "%d", v); send_byte(v[7:0]); end
                wait (nrx >= w);
                repeat (4 * CPB) @(posedge clk);
            end
        end
        $fclose(frx);
        $display("tb_top done, %0d bytes received", nrx);
        $finish;
    end
endmodule
