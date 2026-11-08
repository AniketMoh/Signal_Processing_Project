// uart_rx.v -- UART receiver, 8 data bits, no parity, 1 stop bit (8N1), LSB first.  CLKS_PER_BIT = f_clk / baud
// (100 for 1 Mbaud at 100 MHz).  The input is synchronised with two flip-flops and then filtered: the filtered line changes
// only after the synchronised input has kept its new value for GLITCH clocks, so short spikes on the pin cannot start a
// false byte or flip a bit.  Each bit is decided by a majority of three filtered samples around its middle.
// ferr pulses for a byte whose stop bit is 0 (framing error; the byte is dropped).
// Level L3.  Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module uart_rx #(
    parameter CLKS_PER_BIT = 100,
    parameter GLITCH       = 4            // clocks a new input level must persist (40 ns at 100 MHz)
)(
    input  wire       clk,
    input  wire       rst,
    input  wire       rxd,
    output reg  [7:0] data,
    output reg        valid,      // one clock when 'data' holds a new byte
    output reg        ferr        // one clock on a framing error
);
    localparam CW = $clog2(CLKS_PER_BIT + 1);
    reg [1:0]    sync = 2'b11;
    reg          rxf  = 1'b1;     // filtered line
    reg [2:0]    gcnt = 3'd0;
    reg [2:0]    hist = 3'b111;   // last three filtered samples (majority vote)
    reg [1:0]    state;           // 0 idle, 1 start bit, 2 data bits, 3 stop bit
    reg [CW-1:0] cnt;
    reg [2:0]    nbit;
    reg [7:0]    sh;
    wire maj = (hist[0] & hist[1]) | (hist[1] & hist[2]) | (hist[0] & hist[2]);
    always @(posedge clk) begin
        sync <= {sync[0], rxd};
        if (sync[1] == rxf) gcnt <= 3'd0;
        else if (gcnt == GLITCH - 1) begin rxf <= sync[1]; gcnt <= 3'd0; end
        else gcnt <= gcnt + 3'd1;
        hist  <= {hist[1:0], rxf};
        valid <= 1'b0;
        ferr  <= 1'b0;
        if (rst) begin
            state <= 2'd0;
        end else case (state)
            // the filtered line has just gone low: middle of the start bit after half a bit (the vote is centred on it)
            2'd0: if (!rxf) begin state <= 2'd1; cnt <= CLKS_PER_BIT / 2 - 1; end
            2'd1: if (cnt == 0) begin
                      if (!maj) begin state <= 2'd2; cnt <= CLKS_PER_BIT - 1; nbit <= 3'd0; end
                      else state <= 2'd0;                                  // not a start bit
                  end else cnt <= cnt - 1'b1;
            2'd2: if (cnt == 0) begin
                      sh  <= {maj, sh[7:1]};
                      cnt <= CLKS_PER_BIT - 1;
                      if (nbit == 3'd7) state <= 2'd3;
                      nbit <= nbit + 3'd1;
                  end else cnt <= cnt - 1'b1;
            2'd3: if (cnt == 0) begin
                      state <= 2'd0;
                      if (maj) begin data <= sh; valid <= 1'b1; end
                      else ferr <= 1'b1;                                   // framing error: byte dropped
                  end else cnt <= cnt - 1'b1;
        endcase
    end
endmodule
