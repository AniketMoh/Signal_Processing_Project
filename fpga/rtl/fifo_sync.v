// fifo_sync.v -- synchronous FIFO in block RAM.  rd_en with empty = 0 pops one word; dout holds it from the next clock on.
// 'clear' empties the FIFO.  count = words stored.
// Level L3.  Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module fifo_sync #(
    parameter W  = 8,
    parameter AW = 12               // depth 2^AW words
)(
    input  wire          clk,
    input  wire          clear,
    input  wire          wr_en,
    input  wire [W-1:0]  din,
    input  wire          rd_en,
    output reg  [W-1:0]  dout,
    output wire          empty,
    output wire          full,
    output wire [AW:0]   count
);
    (* ram_style = "block" *) reg [W-1:0] mem [0:(1 << AW) - 1];
    reg [AW:0] wp = 0, rp = 0;
    assign count = wp - rp;
    assign empty = (wp == rp);
    assign full  = (count == (1 << AW));
    always @(posedge clk) begin
        if (wr_en && !full) mem[wp[AW-1:0]] <= din;
        if (rd_en && !empty) dout <= mem[rp[AW-1:0]];
    end
    always @(posedge clk) begin
        if (clear) begin
            wp <= 0; rp <= 0;
        end else begin
            if (wr_en && !full) wp <= wp + 1'b1;
            if (rd_en && !empty) rp <= rp + 1'b1;
        end
    end
endmodule
