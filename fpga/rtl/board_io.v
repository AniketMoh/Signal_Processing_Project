// board_io.v -- Boolean Board helpers: button debouncer, switch synchroniser, two 4-digit seven-segment displays (decimal).
// Boolean Board: buttons and LEDs active high; seven-segment anodes and segments active low (Real Digital reference manual);
// segment order assumed SEG[0..6] = a..g, SEG[7] = decimal point.
// Level L3.  Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.

// debounce: output follows the (synchronised) input after it has been stable for 2^N clocks (N = 20: about 10 ms at 100 MHz)
module debounce #(
    parameter N = 20
)(
    input  wire clk,
    input  wire in,
    output reg  out = 1'b0,
    output reg  rise          // one clock on a 0 -> 1 change of out
);
    reg [1:0]   s = 2'b00;
    reg [N-1:0] cnt = 0;
    always @(posedge clk) begin
        s    <= {s[0], in};
        rise <= 1'b0;
        if (s[1] == out) cnt <= 0;
        else begin
            cnt <= cnt + 1'b1;
            if (&cnt) begin out <= s[1]; rise <= s[1]; end
        end
    end
endmodule

// two displays of 4 decimal digits each, values 0..9999 (larger values show 9999), multiplexed at about 1.5 kHz per digit
module sevenseg2 (
    input  wire        clk,
    input  wire [13:0] val0,      // display 0
    input  wire [13:0] val1,      // display 1
    output reg  [3:0]  an0,
    output reg  [7:0]  seg0,
    output reg  [3:0]  an1,
    output reg  [7:0]  seg1
);
    function [15:0] bcd4;          // binary 0..9999 -> 4 BCD digits (double dabble)
        input [13:0] b;
        integer i;
        reg [29:0] x;
        begin
            x = {16'd0, b};
            for (i = 0; i < 14; i = i + 1) begin
                if (x[17:14] > 4) x[17:14] = x[17:14] + 4'd3;
                if (x[21:18] > 4) x[21:18] = x[21:18] + 4'd3;
                if (x[25:22] > 4) x[25:22] = x[25:22] + 4'd3;
                if (x[29:26] > 4) x[29:26] = x[29:26] + 4'd3;
                x = x << 1;
            end
            bcd4 = x[29:14];
        end
    endfunction
    function [7:0] font;           // active-low segments, bit 0 = a ... bit 6 = g, bit 7 = dp (off)
        input [3:0] d;
        case (d)
            4'd0: font = 8'b11000000;  4'd1: font = 8'b11111001;  4'd2: font = 8'b10100100;  4'd3: font = 8'b10110000;
            4'd4: font = 8'b10011001;  4'd5: font = 8'b10010010;  4'd6: font = 8'b10000010;  4'd7: font = 8'b11111000;
            4'd8: font = 8'b10000000;  4'd9: font = 8'b10010000;  default: font = 8'b11111111;
        endcase
    endfunction

    reg [15:0] d0, d1;
    reg [17:0] div = 0;
    wire [1:0] k = div[17:16];
    always @(posedge clk) begin
        div <= div + 1'b1;
        d0  <= bcd4((val0 > 14'd9999) ? 14'd9999 : val0);
        d1  <= bcd4((val1 > 14'd9999) ? 14'd9999 : val1);
        an0 <= ~(4'b0001 << k);
        an1 <= ~(4'b0001 << k);
        seg0 <= font(d0[4*k +: 4]);
        seg1 <= font(d1[4*k +: 4]);
    end
endmodule
