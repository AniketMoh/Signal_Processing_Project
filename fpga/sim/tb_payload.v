// tb_payload.v -- top_boolean in payload mode with a UART model.  Reads {DIR}/cmds.txt (groups "K W b0 ... b(K-1)": send K bytes,
// then wait until W bytes in total have been received), writes every received byte to {DIR}/rx.txt and every audio sample
// that the playback logic outputs to {DIR}/play.txt.  Fast settings: 16 clocks per UART bit, a decision-word buffer of only
// 2^TX_AW words (so the output-full pause is exercised), short audio tick and prebuffer.  Level L3.
// Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
`timescale 1ns/1ps
module tb_payload;
    parameter CPB    = 16;
    parameter TX_AW  = 3;
    parameter TICK   = 300;
    parameter PREBUF = 8;
    parameter SW     = 16'h0000;
    parameter DIR    = "vec";
    parameter MAXCLK = 80000000;

    reg clk = 0;
    always #5 clk = ~clk;
    reg  [15:0] sw = SW;
    reg  [3:0]  btn = 4'd0;
    reg         rxd = 1'b1;
    wire        txd, aud_l, aud_r;
    wire [15:0] led;
    wire [2:0]  rgb0, rgb1;
    wire [3:0]  an0, an1;
    wire [7:0]  seg0, seg1;

    top_boolean #(.CLKS_PER_BIT(CPB), .DEB_N(4), .WIN_LOG2(8), .PAY_WIN_LOG2(6), .DEMO_NT(1500), .TICK(TICK),
                  .PAY_TX_AW(TX_AW), .PLAY_PREBUF(PREBUF)) dut (
        .clk(clk), .sw(sw), .btn(btn), .led(led), .RGB0(rgb0), .RGB1(rgb1), .D0_AN(an0), .D0_SEG(seg0), .D1_AN(an1), .D1_SEG(seg1),
        .UART_rxd(rxd), .UART_txd(txd), .left_audio_out(aud_l), .right_audio_out(aud_r));

    integer frx, fpl, nrx = 0, nhold = 0, b;
    reg [7:0] rb;
    always begin
        @(negedge txd);
        repeat (CPB / 2) @(posedge clk);
        if (txd == 1'b0) begin
            for (b = 0; b < 8; b = b + 1) begin repeat (CPB) @(posedge clk); rb[b] = txd; end
            repeat (CPB) @(posedge clk);
            if (txd !== 1'b1) $display("ERROR tb_payload: framing error on txd");
            $fdisplay(frx, "%0d", rb);
            nrx = nrx + 1;
        end
    end
    always @(posedge clk) if (dut.u_pay.pl_got) $fdisplay(fpl, "%0d", dut.u_pay.pl_dout);
    always @(posedge clk) if (dut.u_pay.hold && dut.pay_mode) nhold = nhold + 1;

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
        if (nclk == MAXCLK) begin $display("ERROR tb_payload: timeout"); $fclose(frx); $fclose(fpl); $finish; end
    end
    initial begin
        fc  = $fopen({DIR, "/cmds.txt"}, "r");
        frx = $fopen({DIR, "/rx.txt"}, "w");
        fpl = $fopen({DIR, "/play.txt"}, "w");
        repeat (400) @(posedge clk);
        while (!$feof(fc)) begin
            st = $fscanf(fc, "%d %d", k, w);
            if (st == 2) begin
                for (i = 0; i < k; i = i + 1) begin st = $fscanf(fc, "%d", v); send_byte(v[7:0]); end
                wait (nrx >= w);
                repeat (4 * CPB) @(posedge clk);
                // a new experiment empties the audio buffer: let the playback of this one finish first
                while (dut.u_pay.playing || !dut.u_pay.pl_empty) @(posedge clk);
            end
        end
        $fclose(frx); $fclose(fpl);
        $display("tb_payload done, %0d bytes received, %0d clocks with the output buffer full", nrx, nhold);
        $finish;
    end
endmodule
