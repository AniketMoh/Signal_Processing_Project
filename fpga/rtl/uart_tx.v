// uart_tx.v -- UART transmitter, 8N1, LSB first.  CLKS_PER_BIT = f_clk / baud.  'start' with 'data' when ready = 1.
// Level L3.  Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module uart_tx #(
    parameter CLKS_PER_BIT = 868
)(
    input  wire       clk,
    input  wire       rst,
    input  wire       start,
    input  wire [7:0] data,
    output reg        txd,
    output wire       ready
);
    localparam CW = $clog2(CLKS_PER_BIT + 1);
    reg [9:0]    sh;             // stop bit, 8 data bits, start bit (sent from bit 0)
    reg [3:0]    nbit;           // bits still to send
    reg [CW-1:0] cnt;
    assign ready = (nbit == 4'd0) && (cnt == 0);          // also waits for the whole stop bit
    always @(posedge clk) begin
        if (rst) begin
            txd <= 1'b1; nbit <= 4'd0; cnt <= 0;
        end else if (ready) begin
            txd <= 1'b1;
            if (start) begin
                sh   <= {1'b1, data, 1'b0};
                nbit <= 4'd10;
                cnt  <= 0;
            end
        end else if (cnt == 0) begin
            txd  <= sh[0];
            sh   <= {1'b1, sh[9:1]};
            cnt  <= CLKS_PER_BIT - 1;
            nbit <= nbit - 4'd1;
        end else begin
            cnt <= cnt - 1'b1;
        end
    end
endmodule
