// lfsr_noise.v -- FPGA-style Gaussian-like noise: sum of 12 uniform numbers, each uniform number built from 16 bits of its own LFSR.
// Level L3 (RTL simulation).  Must match fxp_lib._lfsr_noise (level L2) bit for bit.
//
// How it works (same as the Python model):
//   * 12 Fibonacci LFSRs, LFSR number i has n_i bits and feedback taps (n_i, k_i)  [trinomials x^n + x^k + 1].
//   * In every clock cycle with en = 1 each LFSR gives one output bit (its lowest bit, taken BEFORE the shift) and then shifts.
//   * After 16 such cycles every LFSR has produced a 16-bit word (first bit = most significant bit).
//   * S = sum of the 12 words (unsigned, 20 bits).  The noise sample in units of 2^-16 is   noise_int = S - 393210
//     (this is  (S + 6)/65536 - 6  scaled by 65536: the 12 values (word + 1/2)/65536 are added and 6 is subtracted).
//   * The real noise is  sigma * noise_int / 65536  (sigma scaling is done in a later block, not here).
// One noise sample is ready every 16 enabled clock cycles ('valid' is high for one clock when 'noise' has a new value).
module lfsr_noise (
    input  wire               clk,
    input  wire               rst,       // synchronous reset: counter to 0
    input  wire               load,      // load the 12 start values from 'seeds' (also restarts the 16-cycle counter)
    input  wire [12*36-1:0]   seeds,     // 12 start values, 36 bits each, LFSR i in bits [36*i +: 36]
    input  wire               en,        // run
    output reg  signed [19:0] noise,     // noise_int (units of 2^-16), range +-393210
    output reg                valid
);
    // (n, k) of the 12 LFSRs, as in fxp_lib.LFSR_TAPS
    function integer tap_n;
        input integer i;
        begin
            case (i)
                0: tap_n = 17;  1: tap_n = 18;  2: tap_n = 20;  3: tap_n = 21;
                4: tap_n = 22;  5: tap_n = 23;  6: tap_n = 25;  7: tap_n = 28;
                8: tap_n = 29;  9: tap_n = 31; 10: tap_n = 33; default: tap_n = 35;
            endcase
        end
    endfunction
    function integer tap_k;
        input integer i;
        begin
            case (i)
                0: tap_k = 14;  1: tap_k = 11;  2: tap_k = 17;  3: tap_k = 19;
                4: tap_k = 21;  5: tap_k = 18;  6: tap_k = 22;  7: tap_k = 25;
                8: tap_k = 27;  9: tap_k = 28; 10: tap_k = 20; default: tap_k = 33;
            endcase
        end
    endfunction

    reg  [35:0] st   [0:11];      // LFSR states (only the lowest n_i bits are used, the rest stay 0)
    reg  [14:0] part [0:11];      // first 15 bits of the word being built
    reg  [3:0]  cnt;              // counts 0..15

    wire [15:0] word [0:11];      // completed word at the 16th step
    wire [19:0] sum_words;

    genvar g;
    generate
        for (g = 0; g < 12; g = g + 1) begin : gw
            assign word[g] = {part[g], st[g][0]};
        end
    endgenerate

    assign sum_words = word[0] + word[1] + word[2] + word[3] + word[4] + word[5]
                     + word[6] + word[7] + word[8] + word[9] + word[10] + word[11];

    integer i;
    reg fb;
    always @(posedge clk) begin
        valid <= 1'b0;
        if (rst) begin
            cnt <= 4'd0;
        end else if (load) begin
            for (i = 0; i < 12; i = i + 1) begin
                st[i]   <= seeds[36*i +: 36];
                part[i] <= 15'd0;
            end
            cnt <= 4'd0;
        end else if (en) begin
            if (cnt == 4'd15) begin
                // 16th bit is on st[i][0] now: the word is complete -> output the sum, start a new word
                noise <= $signed({1'b0, sum_words}) - 21'sd393210;
                valid <= 1'b1;
            end
            for (i = 0; i < 12; i = i + 1) begin
                part[i] <= {part[i][13:0], st[i][0]};                       // take the output bit (before the shift)
                fb = st[i][0] ^ st[i][tap_n(i) - tap_k(i)];                  // feedback = bit0 xor bit(n-k)
                st[i] <= (st[i] >> 1) | ({35'd0, fb} << (tap_n(i) - 1));     // shift right, feedback into bit n-1
            end
            cnt <= cnt + 4'd1;                                               // wraps 15 -> 0
        end
    end
endmodule
