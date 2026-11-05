// payload_lfsr.v -- on-chip payload bits for the board: maximal-length LFSR x^31 + x^28 + 1 (period 2^31 - 1), independent of the
// 15-bit training PRBS.  Same convention as prbs15.v and lms_lib.lfsr_bits(n, nbits=31, taps=(31, 28), seed): bit_out is the lowest
// register bit BEFORE the shift; feedback = bit0 xor bit3 goes into bit 30.  So the host can regenerate the exact payload with
//     lms_lib.lfsr_bits(n, 31, (31, 28), seed)
// Level L3.  Responsible member: Aniket Mohapatra (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module payload_lfsr (
    input  wire        clk,
    input  wire        load,       // load the start value (must be nonzero; 0 is replaced by 1)
    input  wire [30:0] seed,
    input  wire        en,         // advance one bit
    output wire        bit_out
);
    reg [30:0] st = 31'd1;
    assign bit_out = st[0];
    always @(posedge clk) begin
        if (load)    st <= (seed == 31'd0) ? 31'd1 : seed;
        else if (en) st <= {st[0] ^ st[3], st[30:1]};
    end
endmodule
