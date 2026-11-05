// uart_rx.v -- UART receiver, 8 data bits, no parity, 1 stop bit (8N1), LSB first.  CLKS_PER_BIT = f_clk / baud
// (868 for 115200 baud at 100 MHz).  The input is synchronised with two flip-flops; each bit is sampled in its middle.
// Level L3.  Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module uart_rx #(
    parameter CLKS_PER_BIT = 868
)(
    input  wire       clk,
    input  wire       rst,
    input  wire       rxd,
    output reg  [7:0] data,
    output reg        valid      // one clock when 'data' holds a new byte
);
    localparam CW = $clog2(CLKS_PER_BIT + 1);
    reg [2:0]    sync = 3'b111;
    reg [1:0]    state;          // 0 idle, 1 start bit, 2 data bits, 3 stop bit
    reg [CW-1:0] cnt;
    reg [2:0]    nbit;
    reg [7:0]    sh;
    wire rx = sync[2];
    always @(posedge clk) begin
        sync  <= {sync[1:0], rxd};
        valid <= 1'b0;
        if (rst) begin
            state <= 2'd0;
        end else case (state)
            2'd0: if (!rx) begin state <= 2'd1; cnt <= CLKS_PER_BIT / 2; end
            2'd1: if (cnt == 0) begin
                      if (!rx) begin state <= 2'd2; cnt <= CLKS_PER_BIT - 1; nbit <= 3'd0; end
                      else state <= 2'd0;                                  // glitch, not a start bit
                  end else cnt <= cnt - 1'b1;
            2'd2: if (cnt == 0) begin
                      sh  <= {rx, sh[7:1]};
                      cnt <= CLKS_PER_BIT - 1;
                      if (nbit == 3'd7) state <= 2'd3;
                      nbit <= nbit + 3'd1;
                  end else cnt <= cnt - 1'b1;
            2'd3: if (cnt == 0) begin
                      state <= 2'd0;
                      if (rx) begin data <= sh; valid <= 1'b1; end            // framing error: byte dropped
                  end else cnt <= cnt - 1'b1;
        endcase
    end
endmodule
