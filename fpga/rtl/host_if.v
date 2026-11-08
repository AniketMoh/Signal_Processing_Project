// host_if.v -- command interface to the PC over the USB-UART (8N1, 1 Mbaud by default).  All multi-byte fields little-endian.
//   'I'            -> identification: "LMSF", B_MUL, B_ACC, RND, version (8 bytes; version 2 = payload transport)
//   'X' + 81 bytes -> configure and start one experiment; the report is sent automatically when it is done
//                     p(1) S(2) c_lo(1) c_hi(1) flags(1) sigma_q(3) n_t(4) n_total(4) pay_seed(4) seeds(12 x 5, 36 bits each)
//                     flags: bit0 static channel, bit1 payload from the PC, bit2 play the payload on the board's audio output
//   'Q'            -> report now (current counters)
//   'S'            -> stop the running experiment (a report follows)
//   'D'            -> link diagnostics: "DBG", bytes received(4), framing errors(4), payload bytes accepted(4),
//                     payload bytes dropped because the payload buffer was full(4)  (19 bytes; counters since reset)
// Payload mode (flags bit1): every byte received after the 'X' frame is payload (payload_io.v) until the run ends; the run also
// ends when no byte has arrived for PAY_TIMEOUT clocks (0.5 s).  During the run the board sends one 3-byte word per 8 payload
// bits (R1, R2, R3 decisions, delay-aligned); the report follows the last word.
// Report (48 bytes): A5 5A, status(1: bit0 running, bit1 done, bit2 tracking, bit3 host mode, bit4 payload mode), sym_idx(4),
//                    n_eval(4), err1(4), err2(4), err3(4), sse2(8), sse3(8), stalls(4), updates(4),
//                    checksum(1) = XOR of the 45 bytes after A5 5A.
// A command whose bytes stop arriving for about 50 ms is discarded.
// Level L3.  Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module host_if #(
    parameter CLKS_PER_BIT = 100,
    parameter B_MUL = 12,
    parameter B_ACC = 16,
    parameter RND   = 1,
    parameter TIMEOUT = 5000000,         // clocks without a byte inside a command (50 ms at 100 MHz)
    parameter PAY_TIMEOUT = 50000000     // clocks without a payload byte before a payload run is ended (0.5 s)
)(
    input  wire              clk,
    input  wire              rst,
    input  wire              rxd,
    output wire              txd,
    // configuration written by the host
    output reg  [3:0]        p_in,
    output reg  [15:0]       S,
    output reg  [6:0]        c_lo,
    output reg  [6:0]        c_hi,
    output reg               static_mode,
    output reg  [16:0]       sigma_q,
    output reg  [31:0]       n_t,
    output reg  [31:0]       n_total,
    output reg  [30:0]       pay_seed,
    output reg  [12*36-1:0]  seeds,
    output reg               start,          // one clock: start the experiment configured above
    output reg               stop,
    output reg               host_mode,      // set by 'X'; cleared by clear_host
    input  wire              clear_host,
    output reg               pay_mode,       // payload bytes come from the PC (until the run ends)
    output reg               play_en,
    output reg  [7:0]        pay_byte,
    output reg               pay_valid,
    // decision words from payload_io
    output reg               word_rd,
    input  wire [23:0]       word,
    input  wire              word_empty,
    // experiment state
    input  wire              running,
    input  wire              done,
    input  wire              tracking,
    input  wire [31:0]       sym_idx, n_eval, err1, err2, err3,
    input  wire [63:0]       sse2, sse3,
    input  wire [31:0]       stalls, updates,
    input  wire              pay_drop        // a payload byte arrived while the payload buffer was full
);
    localparam NCFG = 81;

    wire [7:0] rx_data;
    wire       rx_valid;
    wire       rx_ferr;
    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_rx (.clk(clk), .rst(rst), .rxd(rxd), .data(rx_data), .valid(rx_valid), .ferr(rx_ferr));
    reg [31:0] n_rx = 0, n_ferr = 0, n_pay = 0, n_drop = 0;      // link diagnostics ('D')
    always @(posedge clk) begin
        if (rx_valid)  n_rx   <= n_rx + 1'b1;
        if (rx_ferr)   n_ferr <= n_ferr + 1'b1;
        if (pay_valid) n_pay  <= n_pay + 1'b1;
        if (pay_drop)  n_drop <= n_drop + 1'b1;
    end

    reg  [7:0] tx_data;
    reg        tx_start;
    wire       tx_ready;
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_tx (.clk(clk), .rst(rst), .start(tx_start), .data(tx_data), .txd(txd), .ready(tx_ready));

    // ---- receive ----
    reg [8*NCFG-1:0] cbuf;
    reg [6:0]        ncnt;            // configuration bytes still expected
    reg [22:0]       idle;
    reg [25:0]       pidle;
    reg              send_id, send_q, send_d, done_d, apply, rep_pending;
    reg [1:0]        arm;             // clocks after a start during which the previous run's 'done' is ignored
    reg [5:0]        settle;          // after the end of a run: let the last decision word reach the FIFO
    integer i;
    always @(posedge clk) begin
        start <= 1'b0; stop <= 1'b0; send_id <= 1'b0; send_q <= 1'b0; send_d <= 1'b0; apply <= 1'b0; pay_valid <= 1'b0;
        done_d <= done;
        if (rst) begin
            ncnt <= 7'd0; host_mode <= 1'b0; idle <= 23'd0; pay_mode <= 1'b0; play_en <= 1'b0; pidle <= 26'd0; arm <= 2'd0;
        end else begin
            if (arm != 2'd0) arm <= arm - 2'd1;
            if (clear_host) begin host_mode <= 1'b0; pay_mode <= 1'b0; end
            if (ncnt != 0 && !rx_valid) begin
                idle <= idle + 23'd1;
                if (idle == TIMEOUT[22:0]) ncnt <= 7'd0;
            end
            if (pay_mode) begin
                if (done && arm == 2'd0) pay_mode <= 1'b0;                   // run finished: back to commands
                else if (rx_valid) pidle <= 26'd0;
                else if (pidle == PAY_TIMEOUT[25:0]) begin stop <= 1'b1; pay_mode <= 1'b0; end
                else pidle <= pidle + 26'd1;
            end
            if (rx_valid) begin
                idle <= 23'd0;
                if (pay_mode && !(done && arm == 2'd0)) begin
                    pay_byte <= rx_data; pay_valid <= 1'b1;
                end else if (ncnt != 0) begin
                    cbuf <= {rx_data, cbuf[8*NCFG-1:8]};
                    ncnt <= ncnt - 7'd1;
                    if (ncnt == 7'd1) apply <= 1'b1;
                end else case (rx_data)
                    "I": send_id <= 1'b1;
                    "D": send_d  <= 1'b1;
                    "Q": send_q  <= 1'b1;
                    "S": stop    <= 1'b1;
                    "X": ncnt    <= NCFG[6:0];
                    default: ;
                endcase
            end
            if (apply) begin
                p_in        <= cbuf[0 +: 4];
                S           <= cbuf[8 +: 16];
                c_lo        <= cbuf[24 +: 7];
                c_hi        <= cbuf[32 +: 7];
                static_mode <= cbuf[40];
                pay_mode    <= cbuf[41];
                play_en     <= cbuf[42];
                sigma_q     <= cbuf[48 +: 17];
                n_t         <= cbuf[72 +: 32];
                n_total     <= cbuf[104 +: 32];
                pay_seed    <= cbuf[136 +: 31];
                for (i = 0; i < 12; i = i + 1) seeds[36*i +: 36] <= cbuf[168 + 40*i +: 36];
                host_mode   <= 1'b1;
                start       <= 1'b1;
                pidle       <= 26'd0;
                arm         <= 2'd3;
            end
        end
    end

    // ---- transmit: identification, decision words, reports; a report at the end of a run waits for the last word ----
    reg [8*46-1:0] tbuf;              // bytes still to send, next byte in [7:0]
    reg [5:0]      tleft;
    reg            hdr2;              // the second header byte (5A) of a report is still to be sent
    reg            busy, wpend, wpend2, id_pend, q_pend, d_pend;
    wire [7:0] status = {3'd0, pay_mode, host_mode, tracking, done, running};
    wire [8*45-1:0] rep = {updates, stalls, sse3, sse2, err3, err2, err1, n_eval, sym_idx, status};
    function [7:0] xor_bytes;
        input [8*45-1:0] b;
        integer j;
        begin
            xor_bytes = 8'd0;
            for (j = 0; j < 45; j = j + 1) xor_bytes = xor_bytes ^ b[8*j +: 8];
        end
    endfunction
    always @(posedge clk) begin
        tx_start <= 1'b0;
        word_rd  <= 1'b0;
        if (rst) begin
            tleft <= 6'd0; busy <= 1'b0; wpend <= 1'b0; wpend2 <= 1'b0; rep_pending <= 1'b0; settle <= 6'd0;
            id_pend <= 1'b0; q_pend <= 1'b0; d_pend <= 1'b0;
        end else begin
            if (send_id) id_pend <= 1'b1;
            if (send_d)  d_pend  <= 1'b1;
            if (send_q)  q_pend  <= 1'b1;
            wpend2 <= wpend;                                     // FIFO output is valid two clocks after word_rd is set
            wpend  <= 1'b0;
            if (done && !done_d && host_mode) begin rep_pending <= 1'b1; settle <= 6'd0; end
            else if (rep_pending && settle != 6'd63) settle <= settle + 6'd1;
            if (wpend2) begin                                    // a decision word was read: send it, R1 byte first
                tbuf    <= {{43{8'h00}}, word[7:0], word[15:8]};
                tx_data <= word[23:16]; tx_start <= 1'b1;
                tleft   <= 6'd2; hdr2 <= 1'b0; busy <= 1'b1;
            end else if (!busy) begin
                if (id_pend) begin
                    id_pend <= 1'b0;
                    tbuf    <= {{38{8'h00}}, 8'd2, RND[7:0], B_ACC[7:0], B_MUL[7:0], "F", "S", "M"};
                    tx_data <= "L"; tx_start <= 1'b1;
                    tleft   <= 6'd7; hdr2 <= 1'b0; busy <= 1'b1;
                end else if (d_pend) begin
                    d_pend  <= 1'b0;
                    tbuf    <= {{28{8'h00}}, n_drop, n_pay, n_ferr, n_rx, "G", "B"};
                    tx_data <= "D"; tx_start <= 1'b1;
                    tleft   <= 6'd18; hdr2 <= 1'b0; busy <= 1'b1;
                end else if (!word_empty) begin
                    word_rd <= 1'b1; wpend <= 1'b1; busy <= 1'b1;
                end else if (q_pend || (rep_pending && settle == 6'd63)) begin
                    rep_pending <= 1'b0; q_pend <= 1'b0;
                    tbuf    <= {xor_bytes(rep), rep};
                    tx_data <= 8'hA5; tx_start <= 1'b1;
                    tleft   <= 6'd47;                            // 5A + 45 bytes + checksum
                    hdr2    <= 1'b1; busy <= 1'b1;
                end
            end else if (tx_ready && !tx_start && !wpend && !wpend2 && !word_rd) begin
                if (tleft == 0) busy <= 1'b0;
                else begin
                    if (hdr2) begin tx_data <= 8'h5A; hdr2 <= 1'b0; end
                    else begin tx_data <= tbuf[7:0]; tbuf <= {8'h00, tbuf[8*46-1:8]}; end
                    tx_start <= 1'b1;
                    tleft    <= tleft - 6'd1;
                end
            end
        end
    end
endmodule
