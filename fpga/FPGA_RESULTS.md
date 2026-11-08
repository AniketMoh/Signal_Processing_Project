# FPGA results — P7 to P10 (6 Nov 2026)

Board: Real Digital Boolean Board, Spartan-7 XC7S50-1CSGA324C, 100 MHz. Tools: Vivado 2025.2, iverilog.
Default build: B_mul = 12, B_acc = 16, round to nearest (the mid-term L2 recommendation); B_acc = 26 (the L2 baseline) built and measured as well.
Level labels as in the project: **L2** bit-true model, **L3** RTL simulation, **L4** Vivado synthesis/implementation, **L5** measured on the board. Every number below is labelled. Supervised LMS throughout (the transmitted symbol is the LMS reference after training).

## 1. Summary
1. **The board reproduces the bit-true model exactly.** For 8 configurations (μ 2⁻⁵…2⁻¹¹, S 1…1000 and static, both channels, 6–14 dB; 3.4 million symbols) the board's error counters, squared-error sums and stall counters are identical to the L2 model, for both B_acc = 16 and B_acc = 26 (**L5 = L2**, `host/results/board_verify_*.json`).
2. **The design fits and meets 100 MHz.** Full design: 51 of 120 DSP48E1, 4825 LUT (15 %), 4670 FF (7 %), no block RAM, worst setup slack +0.298 ns (**L4**). The PPR-22 estimate was 51 DSP for the datapath and the audit's ≈ 54 including counters; measured is 51 because the channel FIR needs no multiplier (taps are ±1 times a 7-bit counter and a constant).
3. **The LMS update stays plain LMS (D = 0).** One symbol every 16 clocks (6.25 Msymbol/s); the LMS work of a symbol takes 10 clocks and finishes before the next symbol starts. No delay was introduced into the adaptation loop.
4. **On the board the tracking picture of L1/L2 appears** (**L5**, figure `host/results/fig_L5_board_tracking.png`): R1 and R2 do not depend on the variation rate; R3 degrades as the channel changes faster; the smaller μ, the slower the rate at which it starts to degrade; and which μ is best depends on the rate.
5. **Accumulator width (16 against 26 bits) does not change tracking on the board** although 16 bits stalls 6.6 % (μ = 2⁻⁸) to 20 % (μ = 2⁻¹⁰) of all coefficient updates: R3 BER and MSE agree to 3–4 significant digits at every S (**L5**). The 16-bit build saves 318 flip-flops; DSP count is the same (**L4**).

## 2. Verification (L3)
| Test | What | Result | Log |
|---|---|---|---|
| LMS core | `lms_rx_syn` vs `fxp_lib.fxp_receivers`: 5 mid-term cases + 7 new (B_acc 12/16/26/32, B_mul 8/12/16, μ 2⁻²…2⁻¹¹, truncation, left-shift update path) + N_T = 30000 run (34 000 symbols) | 0 differing symbols, stall/update counters equal | `sim/results/lms_syn_test_log.txt` |
| Cycle budget (V10) | symbols 10 clocks apart pass; 9 clocks apart (negative control) must be flagged | passes; the negative control is flagged and 3979 of 4000 outputs differ | same |
| Vendor simulator | same testbench in Vivado xsim, 3 cases | identical to iverilog / L2 | `sim/results/lms_syn_xsim_log.txt` |
| Full chain | `rx_chain_syn` vs L2 chain: mid-term cases A–G + 6 new (B_acc 26/32, μ 2⁻⁵ and 2⁻¹¹, B_mul 8, N_T = 30000 over 40 000 symbols, board payload LFSR) | every per-symbol signal and every counter identical | `sim/results/chain_syn_test_log.txt` |
| Top level | `top_boolean` with a UART model: identification + two experiments sent as real command frames | decoded reports identical to L2 | `sim/results/top_test_log.txt` |

## 3. Synthesis and implementation (L4)
**Full design** (`vivado/reports/top_summary.txt`; routed; XC7S50 has 120 DSP48E1, 32 600 LUT, 65 200 FF):

| Build | DSP48E1 | LUT | FF | BRAM | WNS | WHS | Fmax (est.) | Power (est.) |
|---|---|---|---|---|---|---|---|---|
| B_mul 12, B_acc 16 | 51 | 4825 | 4670 | 0 | +0.298 ns | +0.049 ns | 103 MHz | 0.136 W |
| B_mul 12, B_acc 26 | 51 | 4851 | 4988 | 0 | +0.718 ns | +0.022 ns | 108 MHz | 0.138 W |

DSPs: 48 in the LMS core (16 R3 filter, 16 R2 filter, 16 update products with the rounding constant in the post-adder), 1 for σ·noise, 2 for e² of R2 and R3. Critical path of the 16-bit build: the 12-word sum of the noise generator (mid-term `lfsr_noise.v`, used unchanged) into the σ·noise DSP; a pipeline register there is the remedy if a later change needs margin. DRC: no errors; 21 DPIP-1 (DSP input pipelining) advisories. Fmax is the estimate 1/(10 ns − WNS), not a measurement at a higher clock.

**Word-length sweep of the LMS core** (out of context, without I/O; routed at 100 MHz; `vivado/reports/ooc_lms_rx_syn_summary.txt`):

| B_mul \ B_acc | 12 | 14 | 16 | 26 | 32 |
|---|---|---|---|---|---|
| 8  | 48 DSP · 2890 LUT · 1515 FF · +1.36 ns | 48 · 2950 · 1579 · +1.17 | 48 · 3018 · 1643 · +1.88 | 48 · 3077 · 1962 · +1.15 | 48 · 5086 · 2290 · +0.35 |
| 12 | 48 · 2817 · 1515 · +1.62 | 48 · 2942 · 1579 · +1.59 | 48 · 3009 · 1643 · +1.67 | 48 · 3068 · 1962 · +1.86 | 48 · 5080 · 2290 · +0.97 |
| 16 | — (B_acc < B_mul) | — | 48 · 2936 · 1643 · +1.47 | 48 · 3061 · 1962 · +1.01 | 48 · 5066 · 2290 · +1.21 |

- **DSP use is flat (48) at every width**, as predicted in the audit: every product fits one 25 × 18 DSP48E1.
- **Flip-flops grow linearly with B_acc** (32 per accumulator bit: 16 accumulators and their update registers).
- **LUTs are nearly flat up to 26 bits and jump by ≈ 2000 at 32 bits**, where the update word no longer fits the DSP post-adder path and the limiter/accumulator logic widens.
- **Multiplier width costs nothing measurable here** (B_mul only changes the DSP operand width).
- Slack differences of a few hundred ps between neighbouring widths are place-and-route variation, not a trend.
- Combined with the L2 result (B_acc ≥ 16 with rounding preserves S*_MSE at all seven FPGA step sizes) and the L5 comparison below: **the cheapest configuration that preserves tracking is B_mul = 12 (or 8 for MSE-insensitive use), B_acc = 16, rounding.**

## 4. Board measurements (L5)
### 4.1 Board = model, count for count
`host/run_board.py verify`: the PC sends the configuration and noise seeds, the board runs N_T = 30000 training symbols and the tracking part, and returns the counters; the PC runs the L2 model with the same inputs.

| μ | S | channel | Eb/N0 | symbols | errors R1 / R2 / R3 (B_acc 16) | board = L2 (16) | board = L2 (26) |
|---|---|---|---|---|---|---|---|
| 2⁻⁸ | 28 | primary | 10 dB | 400 000 | 18112 / 2534 / 230 | yes | yes |
| 2⁻⁸ | 1000 | primary | 10 dB | 400 000 | 17108 / 2831 / 122 | yes | yes |
| 2⁻⁸ | 5 | primary | 10 dB | 400 000 | 18267 / 2969 / 518 | yes | yes |
| 2⁻⁵ | 1 | primary | 8 dB | 300 000 | 17602 / 2682 / 9696 | yes | yes |
| 2⁻¹¹ | 224 | primary | 12 dB | 300 000 | 10043 / 883 / 10 | yes | yes |
| 2⁻⁸ | static | primary (c = 40) | 10 dB | 300 000 | 274 / 1 / 3 | yes | yes |
| 2⁻⁸ | 50 | control | 14 dB | 300 000 | 134 / 1 / 0 | yes | yes |
| 2⁻⁶ | 112 | primary | 6 dB | 1 000 000 | 82619 / 33928 / 21144 | yes | yes |

"Yes" means all eight counters are equal (symbols evaluated, three error counts, two squared-error sums, stalls, updates). Because the hardware equals L2 exactly, the L2 word-length study of the mid-term is now also a statement about this hardware for these configurations.

### 4.2 BER and MSE against the variation rate
`host/run_board.py sweep`: primary channel, N_T = 30000, ≈ 20 million evaluated symbols per point (whole triangle periods), one noise seed (2000) and payload seed (777); 3–4 s of board time per point. LFSR sum-of-uniforms noise: BER is quoted only down to about 10⁻⁴ (PPR-22 Sec. 4.3, D-12); smaller values in the files are shown for completeness, not as BER claims.

R3 BER at 10 dB (B_acc = 16):

| S | 5000 | 1000 | 224 | 112 | 56 | 28 | 14 | 5 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| μ = 2⁻⁶ | 1.70e-3 | 1.70e-3 | 1.73e-3 | 1.70e-3 | 1.73e-3 | 1.82e-3 | 1.97e-3 | 2.85e-3 | 4.83e-3 |
| μ = 2⁻⁸ | 3.67e-4 | 3.58e-4 | 3.69e-4 | 3.88e-4 | 4.68e-4 | 6.43e-4 | 9.69e-4 | 1.45e-3 | 1.65e-3 |
| μ = 2⁻¹⁰ | 2.51e-4 | 2.51e-4 | 3.26e-4 | 4.52e-4 | 7.17e-4 | 9.77e-4 | 1.13e-3 | 1.22e-3 | 1.23e-3 |

R1 ≈ 4.9e-2 and R2 ≈ 7.1–8.4e-3 at every S (they never adapt, and every window holds whole periods of the trajectory). At 12 dB, μ = 2⁻⁸: R3 2.8e-5 (slow, below the 10⁻⁴ limit) rising to 4.3e-4 at S = 1; R2 3.4e-3.

What it shows:
- **Frozen vs adaptive:** R3 is better than R2 at every rate, by a factor 20 (slow) to 4 (S = 1) at μ = 2⁻⁸ — no S_cross within the grid on the board either, as in L1.
- **Step size:** R3's BER rises 15 % above its slow-variation level at about S = 320 for μ = 2⁻¹⁰, S = 80 for μ = 2⁻⁸ and S = 14 for μ = 2⁻⁶ — each factor of 4 in μ moves the onset by about a factor of 4 in S, the same ordering as the L1 boundaries S*_MSE = 112 / 28 / 10.
- **Gradient noise vs lag:** μ = 2⁻¹⁰ is best for slow variation (S ≥ 224: smallest gradient noise); μ = 2⁻⁸ is best for 112 ≥ S ≥ 14 (it follows the channel, 2⁻¹⁰ lags); for S ≤ 5 μ = 2⁻¹⁰ is best again — neither can follow the channel any more, and the smaller step stays closer to the best fixed filter for the averaged channel (the "plateau" of the spec), while the larger step chases the channel with lag and noise. μ = 2⁻⁶ is worst at every rate at 10 dB (gradient noise). This is the tracking–step-size trade-off measured in hardware.
- These are single-seed board measurements with ≈ 2·10⁷ bits per point; no boundary S* is computed from them (the project's S* criteria need the seed statistics of L1). They are the hardware confirmation of the trend, not a replacement of the L1 boundary.

### 4.3 Accumulator width on the board
| μ | B_acc | stalled updates | R3 BER, S = 5000 / 28 / 1 | R3 MSE, S = 5000 / 28 / 1 |
|---|---|---|---|---|
| 2⁻⁸ | 16 | 6.6 % | 3.67e-4 / 6.43e-4 / 1.65e-3 | 0.0740 / 0.0835 / 0.1036 |
| 2⁻⁸ | 26 | 0.006 % | 3.68e-4 / 6.44e-4 / 1.65e-3 | 0.0740 / 0.0835 / 0.1036 |
| 2⁻¹⁰ | 16 | 20 % | 2.51e-4 / 9.77e-4 / 1.23e-3 | 0.0701 / 0.0920 / 0.0986 |
| 2⁻¹⁰ | 26 | 0.03 % | 2.52e-4 / 9.78e-4 / 1.24e-3 | 0.0701 / 0.0920 / 0.0986 |

With round-to-nearest, a fifth of the updates can be lost without any visible change: the noise dithers the rounding, as in the L2 study (P6A T3). The price of the 26-bit accumulator is 318 flip-flops and nothing in DSPs; its benefit at these μ is nil.

### 4.4 Image and voice through the board (payload transport)
`host/run_payload.py`: the PC streams payload bytes at 1 Mbaud; the board uses them as the transmitted bits, pauses symbol generation while no payload bit is waiting (the symbol sequence is unchanged), and returns the decisions of R1, R2, R3 with their delays removed (R1 0, R2/R3 Delta = 2). Payloads are the mid-term P5 ones: the 128 x 72 x 8-bit image and the 19.9 s, 8 kHz, 8-bit voice recording. **Every returned byte of every receiver equals the L2 model in all 15 runs** (`results/payload/image_metrics.json`, `audio_metrics.json`; PNGs and WAVs in `results/payload/`).

| Image, 10 dB | static | S = 1000 | S = 28 | S = 5 | S = 1 | S = 1, mu = 2^-5 |
|---|---|---|---|---|---|---|
| wrong pixels R1 / R2 / R3 (mu = 2^-8 unless stated) | 53 / 1 / 2 | 2068 / 251 / 16 | 2423 / 365 / 44 | 2432 / 336 / 77 | 2398 / 344 / 89 | 2398 / 464 / 992 |

| Voice, 14 dB, mu = 2^-8 | static | S = 1000 | S = 28 | S = 1 |
|---|---|---|---|---|
| bit errors R1 / R2 / R3 (of 1 271 128) | 0 / 0 / 0 | 27 818 / 1 472 / 2 | 28 822 / 1 593 / 14 | 28 619 / 1 491 / 43 |
| R3 waveform SNR (L1 in the mid-term) | exact | 30.6 dB (29.6) | 24.6 dB (21.7) | 20.9 dB (20.0) |

Link reliability: an early loss of single payload bytes was traced with the board's link counters ('D' command, `host/diag_link.py`) to the PC script reconfiguring the serial port during a transfer; fixed (0 of 30 test runs short afterwards). Payload build (L4): 51 DSP48E1, 5051 LUT, 5111 FF, 4 BRAM tiles, WNS +0.572 ns.

## 5. What was not done / limits
- **Seven-segment digit and segment order** follow the usual convention but are not stated in the board manual; not checked by eye in this session (only the UART path was observed). If digits appear mirrored, the fix is the mapping in `board_io.v`.
- **The bitstream is loaded over JTAG (volatile).** It must be loaded again after a power cycle (`vivado/program_board.tcl`); writing it to the configuration flash was not done.
- **USB-serial dropouts:** twice in about 130 runs the Windows serial port returned "Access is denied" during a run; `run_board.py` now reopens the port and repeats the run (each run restarts from its seeds, so a repeat gives the same counts). No wrong report was ever received (each report has a checksum).
- **Not implemented (optional in PPR-22):** NLMS, decision-directed mode on the board, a delayed-LMS variant (not needed: timing closes without it).
- **Live microphone mode** (`run_payload.py live`, board audio jack via SW[11:10]) is implemented but has not been run or listened to; it is not reported.
- **Post-synthesis functional simulation** was not run separately; the board's exact agreement with L2 is the stronger check of the implemented netlist.
- Board BER values below about 10⁻⁴ are not BER claims (bounded noise, D-12).
