// payload_io.v -- payload transport for the board: bytes from the PC become the transmitted payload bits, and the decisions of
// the three receivers go back to the PC as bytes, already aligned to the transmitted bytes; one receiver can be played on the
// board's PWM audio output at 8 kHz.
//
//   in:   payload bytes (host_if, payload mode) -> RX FIFO -> bits, most significant bit first (np.unpackbits order)
//   out:  for every 8 payload bits one 24-bit word {R1 byte, R2 byte, R3 byte} -> TX FIFO -> host_if (3 bytes, R1 first).
//         R1 decides bit n at tracking symbol n, R2/R3 decide bit n at tracking symbol n+2 (Delta = 2); the packer removes
//         these delays, so byte j of each stream is that receiver's estimate of payload byte j.  The PC therefore sends one
//         padding byte after the payload (the last two R2/R3 decisions fall into it); it yields no output word.
//   play: when play_en = 1 the byte of the receiver chosen by play_sel (0 R3, 1 R2, 2 R1, 3 R3) is also written to a
//         playback FIFO; samples leave it every TICK clocks (8 kHz at 100 MHz) after a 0.25 s prebuffer, as 8-bit unsigned
//         PCM on a PWM output (carrier 100 MHz / 256).  Underflow plays silence (128) and refills the prebuffer; when the
//         stream has stopped for about 32 ms, the samples still buffered are played without waiting for the prebuffer.
// Flow control: bit_avail = a payload bit is ready; hold = the TX FIFO is nearly full.  exp_core stops making symbols while
// a payload bit is needed but not available or while hold = 1; the symbols themselves do not depend on when they are made.
// Level L3.  Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module payload_io #(
    parameter RX_AW   = 12,          // 4096 payload bytes
    parameter TX_AW   = 10,          // 1024 output words (3072 bytes)
    parameter PL_AW   = 13,          // 8192 playback samples (1.02 s)
    parameter TICK    = 12500,       // clocks per audio sample (8 kHz at 100 MHz)
    parameter PREBUF  = 2048         // samples buffered before playback starts (0.25 s)
)(
    input  wire        clk,
    input  wire        clear,        // start of an experiment: empty everything
    // payload bytes in
    input  wire [7:0]  in_byte,
    input  wire        in_valid,
    output wire [RX_AW:0] in_count,
    // payload bits to the chain
    output wire        bit_avail,
    output wire        bit_out,
    input  wire        bit_take,
    // decisions of one tracking symbol
    input  wire        dec_valid,
    input  wire        d1, d2, d3,
    output wire        hold,
    // output words to host_if
    input  wire        tx_rd,
    output wire [23:0] tx_word,      // valid from the clock after tx_rd
    output wire        tx_empty,
    // audio
    input  wire        play_en,
    input  wire [1:0]  play_sel,
    output reg         pwm = 1'b0,
    output reg         playing = 1'b0
);
    // ---- payload bytes -> bits ----
    wire       rx_empty;
    wire [7:0] rx_dout;
    reg        rx_rd = 1'b0, rx_pend = 1'b0, rx_pend2 = 1'b0;   // FIFO output is valid two clocks after rx_rd is set
    reg  [7:0] cur = 8'd0;
    reg  [3:0] left = 4'd0;
    fifo_sync #(.W(8), .AW(RX_AW)) u_rxf (.clk(clk), .clear(clear), .wr_en(in_valid), .din(in_byte),
        .rd_en(rx_rd), .dout(rx_dout), .empty(rx_empty), .full(), .count(in_count));
    assign bit_avail = (left != 4'd0);
    assign bit_out   = cur[7];
    always @(posedge clk) begin
        rx_rd <= 1'b0;
        if (clear) begin
            left <= 4'd0; rx_pend <= 1'b0; rx_pend2 <= 1'b0;
        end else begin
            if (bit_take && left != 4'd0) begin
                cur  <= {cur[6:0], 1'b0};
                left <= left - 4'd1;
            end
            rx_pend2 <= rx_pend && !rx_pend2;                    // one clock, the clock after rx_rd
            if (rx_pend2) begin
                cur <= rx_dout; left <= 4'd8; rx_pend <= 1'b0;
            end else if (left == 4'd0 && !rx_empty && !rx_pend) begin
                rx_rd <= 1'b1; rx_pend <= 1'b1;
            end
        end
    end

    // ---- decisions -> aligned bytes ----
    reg [7:0] s1, s2, s3, h1;
    reg [2:0] n1, n23;
    reg [1:0] skip;
    reg       push;
    reg [23:0] word;
    wire [TX_AW:0] tx_count;
    fifo_sync #(.W(24), .AW(TX_AW)) u_txf (.clk(clk), .clear(clear), .wr_en(push), .din(word),
        .rd_en(tx_rd), .dout(tx_word), .empty(tx_empty), .full(), .count(tx_count));
    assign hold = (tx_count >= (1 << TX_AW) - 4);
    always @(posedge clk) begin
        push <= 1'b0;
        if (clear) begin
            n1 <= 3'd0; n23 <= 3'd0; skip <= 2'd0;
        end else if (dec_valid) begin
            s1 <= {s1[6:0], d1};
            n1 <= n1 + 3'd1;
            if (n1 == 3'd7) h1 <= {s1[6:0], d1};             // R1 byte j is complete two symbols before R2/R3 byte j
            if (skip != 2'd2) skip <= skip + 2'd1;           // R2/R3 decisions of the first two symbols are of bits n-2 < 0
            else begin
                s2 <= {s2[6:0], d2};
                s3 <= {s3[6:0], d3};
                n23 <= n23 + 3'd1;
                if (n23 == 3'd7) begin
                    word <= {h1, {s2[6:0], d2}, {s3[6:0], d3}};     // R2/R3 byte j completes at symbol 8j+9, h1 at 8j+7
                    push <= 1'b1;
                end
            end
        end
    end

    // ---- playback ----
    reg [7:0]  psel;
    wire       pl_empty;
    wire [7:0] pl_dout;
    wire [PL_AW:0] pl_count;
    reg        pl_rd = 1'b0, pl_wr = 1'b0, pl_got = 1'b0;
    reg [13:0] tick = 14'd0;
    reg [7:0]  sample = 8'd128, pc = 8'd0;
    reg [7:0]  quiet = 8'd0;          // audio ticks since the last sample was written (saturates at 255, about 32 ms)
    fifo_sync #(.W(8), .AW(PL_AW)) u_plf (.clk(clk), .clear(clear), .wr_en(pl_wr), .din(psel),
        .rd_en(pl_rd), .dout(pl_dout), .empty(pl_empty), .full(), .count(pl_count));
    always @(posedge clk) begin
        pl_wr <= push && play_en;
        psel  <= (play_sel == 2'd1) ? word[15:8] : (play_sel == 2'd2) ? word[23:16] : word[7:0];
        pl_rd <= 1'b0;
        pl_got <= pl_rd;
        if (pl_got) sample <= pl_dout;
        tick <= (tick == TICK - 1) ? 14'd0 : tick + 14'd1;
        if (pl_wr) quiet <= 8'd0;
        else if (tick == 14'd0 && quiet != 8'd255) quiet <= quiet + 8'd1;
        if (clear) begin
            playing <= 1'b0; sample <= 8'd128;
        end else if (!playing) begin
            sample <= 8'd128;
            // start after the prebuffer, or with whatever is left once the stream has stopped (the end of a recording)
            if (pl_count >= PREBUF || (!pl_empty && quiet == 8'd255)) playing <= 1'b1;
        end else if (tick == 14'd0) begin
            if (pl_empty) begin playing <= 1'b0; sample <= 8'd128; end
            else pl_rd <= 1'b1;
        end
        pc  <= pc + 8'd1;
        pwm <= (pc < sample);
    end
endmodule
