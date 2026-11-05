// prbs15.v -- training sequence generator, x^15 + x^14 + 1, start value 1 (same as lms_lib.lfsr_bits).  Level L3.
// bit_out is the lowest bit of the register BEFORE the shift; the register advances on every clock with en = 1.
module prbs15 (
    input  wire clk,
    input  wire rst,       // synchronous: register = 1
    input  wire en,        // advance one bit
    output wire bit_out
);
    reg [14:0] st;
    assign bit_out = st[0];
    always @(posedge clk) begin
        if (rst) st <= 15'd1;
        else if (en) st <= {st[0] ^ st[1], st[14:1]};    // feedback = bit0 xor bit1 goes into bit 14
    end
endmodule
