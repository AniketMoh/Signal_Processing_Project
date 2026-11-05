// host_if.v -- command interface to the PC over the USB-UART (115200 8N1).  All multi-byte fields little-endian.
//   'I'            -> identification: "LMSF", B_MUL, B_ACC, RND, version (8 bytes)
//   'X' + 81 bytes -> configure and start one experiment; the report is sent automatically when it is done
//                     p(1) S(2) c_lo(1) c_hi(1) flags(1: bit0 static) sigma_q(3) n_t(4) n_total(4) pay_seed(4) seeds(12 x 5, 36 bits each)
//   'Q'            -> report now (current counters)
//   'S'            -> stop the running experiment (a report follows)
// Report (48 bytes): A5 5A, status(1: bit0 running, bit1 done, bit2 tracking, bit3 host mode), sym_idx(4), n_eval(4), err1(4),
//                    err2(4), err3(4), sse2(8), sse3(8), stalls(4), updates(4), checksum(1) = XOR of the 45 bytes after A5 5A.
// A command whose bytes stop arriving for about 50 ms is discarded.
// Level L3.  Responsible member: Gautam Garg (review, verification, viva)
// Written with AI assistance (Claude, Anthropic), project decision D-06.
module host_if #(
    parameter CLKS_PER_BIT = 868,
    parameter B_MUL = 12,
    parameter B_ACC = 16,
    parameter RND   = 1,
    parameter TIMEOUT = 5000000          // clocks without a byte inside a command (50 ms at 100 MHz)
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
    // experiment state
    input  wire              running,
    input  wire              done,
    input  wire              tracking,
    input  wire [31:0]       sym_idx, n_eval, err1, err2, err3,
    input  wire [63:0]       sse2, sse3,
    input  wire [31:0]       stalls, updates
);
    localparam NCFG = 81;

    wire [7:0] rx_data;
    wire       rx_valid;
    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_rx (.clk(clk), .rst(rst), .rxd(rxd), .data(rx_data), .valid(rx_valid));

    reg  [7:0] tx_data;
    reg        tx_start;
    wire       tx_ready;
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_tx (.clk(clk), .rst(rst), .start(tx_start), .data(tx_data), .txd(txd), .ready(tx_ready));

    // ---- receive ----
    reg [8*NCFG-1:0] cbuf;
    reg [6:0]        ncnt;            // configuration bytes still expected
    reg [22:0]       idle;
    reg              send_id, send_rep, done_d, apply;
    integer i;
    always @(posedge clk) begin
        start <= 1'b0; stop <= 1'b0; send_id <= 1'b0; send_rep <= 1'b0; apply <= 1'b0;
        done_d <= done;
        if (rst) begin
            ncnt <= 7'd0; host_mode <= 1'b0; idle <= 23'd0;
        end else begin
            if (clear_host) host_mode <= 1'b0;
            if (ncnt != 0 && !rx_valid) begin
                idle <= idle + 23'd1;
                if (idle == TIMEOUT[22:0]) ncnt <= 7'd0;
            end
            if (rx_valid) begin
                idle <= 23'd0;
                if (ncnt != 0) begin
                    cbuf <= {rx_data, cbuf[8*NCFG-1:8]};
                    ncnt <= ncnt - 7'd1;
                    if (ncnt == 7'd1) apply <= 1'b1;
                end else case (rx_data)
                    "I": send_id  <= 1'b1;
                    "Q": send_rep <= 1'b1;
                    "S": stop     <= 1'b1;
                    "X": ncnt     <= NCFG[6:0];
                    default: ;
                endcase
            end
            if (apply) begin
                p_in        <= cbuf[0 +: 4];
                S           <= cbuf[8 +: 16];
                c_lo        <= cbuf[24 +: 7];
                c_hi        <= cbuf[32 +: 7];
                static_mode <= cbuf[40];
                sigma_q     <= cbuf[48 +: 17];
                n_t         <= cbuf[72 +: 32];
                n_total     <= cbuf[104 +: 32];
                pay_seed    <= cbuf[136 +: 31];
                for (i = 0; i < 12; i = i + 1) seeds[36*i +: 36] <= cbuf[168 + 40*i +: 36];
                host_mode   <= 1'b1;
                start       <= 1'b1;
            end
            if (done && !done_d && host_mode) send_rep <= 1'b1;        // automatic report at the end of a host run
        end
    end

    // ---- transmit: snapshot, then one byte after the other ----
    reg [8*46-1:0] tbuf;              // bytes to send, first byte in [7:0]
    reg [5:0]      tleft;
    reg            hdr2;              // the second header byte (5A) of a report is still to be sent
    reg            busy;
    wire [7:0] status = {4'd0, host_mode, tracking, done, running};
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
        if (rst) begin
            tleft <= 6'd0; busy <= 1'b0;
        end else if (!busy) begin
            if (send_rep) begin
                tbuf  <= {xor_bytes(rep), rep};
                tx_data <= 8'hA5; tx_start <= 1'b1;
                tleft <= 6'd47;                  // 5A + 45 bytes + checksum
                busy  <= 1'b1;
                hdr2  <= 1'b1;
            end else if (send_id) begin
                tbuf  <= {{38{8'h00}}, 8'd1, RND[7:0], B_ACC[7:0], B_MUL[7:0], "F", "S", "M"};
                tx_data <= "L"; tx_start <= 1'b1;
                tleft <= 6'd7;
                busy  <= 1'b1;
                hdr2  <= 1'b0;
            end
        end else if (tx_ready && !tx_start) begin
            if (tleft == 0) busy <= 1'b0;
            else begin
                if (hdr2) begin tx_data <= 8'h5A; hdr2 <= 1'b0; end
                else begin tx_data <= tbuf[7:0]; tbuf <= {8'h00, tbuf[8*46-1:8]}; end
                tx_start <= 1'b1;
                tleft    <= tleft - 6'd1;
            end
        end
    end
endmodule
