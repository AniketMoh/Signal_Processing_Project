// var_ctrl.v -- variation controller: channel counter c.  Level L3.   Same rule as lms_lib.triangle_counter:
//   static at c_lo while run = 0 (training); when run = 1 the counter moves by 1 every S symbols, up from c_lo to c_hi and back down, forever.
//   static_mode = 1 keeps c = c_lo.   'c' is the value used by the CURRENT symbol; the update happens at the end of the symbol (en pulse).
module var_ctrl (
    input  wire        clk,
    input  wire        rst,          // synchronous: c = c_lo
    input  wire        en,           // one pulse per symbol
    input  wire        run,          // 0 during training, 1 from the symbol n = N_T on
    input  wire        static_mode,
    input  wire [6:0]  c_lo,
    input  wire [6:0]  c_hi,
    input  wire [15:0] S,            // symbols per counter step (>= 1)
    output reg  [6:0]  c
);
    reg        up;
    reg [15:0] sc;                   // symbols already spent on the current counter value
    always @(posedge clk) begin
        if (rst) begin
            c  <= c_lo;
            up <= 1'b1;
            sc <= 16'd0;
        end else if (en && run && !static_mode) begin
            if (sc == S - 16'd1) begin
                sc <= 16'd0;
                if (up) begin
                    c <= c + 7'd1;
                    if (c + 7'd1 == c_hi) up <= 1'b0;
                end else begin
                    c <= c - 7'd1;
                    if (c - 7'd1 == c_lo) up <= 1'b1;
                end
            end else begin
                sc <= sc + 16'd1;
            end
        end
    end
endmodule
