# fpga — synthesisable RTL, verification, Vivado flow and board (P7–P10)

Target: Real Digital Boolean Board, Spartan-7 XC7S50 (`xc7s50csga324-1`), 100 MHz. Vivado 2025.2; iverilog for regression.
Results and their levels: **`FPGA_RESULTS.md`**.

The mid-term RTL in `midterm_mtr-22/2_code_and_results_by_phase/09_P7-P8_RTL/` is kept unchanged. Its `lfsr_noise.v` and `prbs15.v` are used as they are; the other blocks were rewritten here for synthesis and must match it and the L2 model (`fxp_lib.py`, `fxp_front.py`) bit for bit.

Every file names its responsible member and states that it was written with AI assistance (decision D-06).

## Levels
L3 = RTL simulation, L4 = Vivado synthesis/implementation, L5 = measured on the board. Out-of-context (OOC) numbers are for the LMS core alone, without I/O; the full-design numbers are in `vivado/reports/top_summary.txt`.

## Layout
| Path | Contents | Responsible |
|---|---|---|
| `rtl/lms_rx_syn.v` | R3 adaptive LMS + R2 frozen bank, real widths, 10-clock sequence per symbol, run-time μ | Pradeep Kumar |
| `rtl/chan_front_syn.v`, `var_ctrl_syn.v`, `rx_chain_syn.v` | Channel + noise front end, variation counter, complete chain with counters | Aniket Mohapatra |
| `rtl/payload_lfsr.v`, `exp_core.v` | On-chip payload (x³¹+x²⁸+1) and run control (load, train, track, stop after N symbols) | Aniket Mohapatra |
| `rtl/uart_rx.v`, `uart_tx.v`, `host_if.v`, `board_io.v` | 115200-baud UART, PC command protocol, debounce, seven-segment displays | Gautam Garg |
| `rtl/top_boolean.v`, `vivado/boolean.xdc` | Board top level (host mode + switch demo), pins | Bhavyam Shankar |
| `sim/` | Testbenches and bit-exact regressions (`run_lms_syn_tests.py`, `run_xsim_check.py`, `run_chain_syn_tests.py`, `run_top_test.py`), shared L2 reference `l2_ref.py`, protocol `protocol.py`; logs in `sim/results/` | per file |
| `vivado/` | `build_top.tcl` (full design + bitstream), `ooc_lms_rx_syn.tcl` (core only), `program_board.tcl`; reports in `vivado/reports/` | Bhavyam Shankar |
| `host/` | `run_board.py` (board vs L2, BER/MSE sweeps), `plot_board.py`; results in `host/results/` | Gautam Garg |
| `report/s_fpga.tex`, `report/figs/board.pdf` | FPGA section for the final report (same LaTeX preamble as `midterm_mtr-22/1_report_source`; insert with `\input{s_fpga}` after the P5–P6 section and copy the figure to `figs/`) | all |
| `vivado/bitstreams/` | Ready bitstreams: `top_boolean_m12_a16_r1.bit` (default, demo) and `top_boolean_m12_a26_r1.bit`; load with `program_board.tcl` (JTAG, volatile) | Bhavyam Shankar |

## Running
```
cd fpga/sim
python run_lms_syn_tests.py        # LMS core vs L2 (15 cases)          needs numpy, numba, iverilog
python run_chain_syn_tests.py      # full chain vs L2 (13 cases)
python run_top_test.py             # top level over the UART model vs L2
python run_xsim_check.py           # LMS core in the Vivado simulator    VIVADO_BIN, default D:/2025.2/Vivado/bin
cd ../vivado
vivado -mode batch -nojournal -log build/top.log -source build_top.tcl -tclargs 12 16 1      # B_MUL B_ACC RND -> bitstream
vivado -mode batch -nojournal -nolog -source program_board.tcl -tclargs build/top_m12_a16_r1/top_boolean.bit
cd ../host
python run_board.py verify         # board counters == L2 counters (needs pyserial; port auto-detected, or --port COM8)
python run_board.py sweep --ebn0 10 --p 8
python plot_board.py
```

## Timing of one symbol
One symbol every 16 clocks (the noise generator needs 16 LFSR steps per sample), i.e. 6.25 Msymbol/s at 100 MHz.
Noise word complete → front end (2 clocks) → LMS (10 clocks: coefficients, products, 2 adder stages, y, e, update products with the rounding constant, μ shift, limit, accumulator write) → counters. The update of symbol n is in the accumulators before symbol n+1 starts, so the algorithm is plain LMS with D = 0, not delayed LMS. The testbenches check the spacing; a negative control at 9 clocks is expected to fail and does.

## Using the board (demo mode, after power-up or BTN0)
| Control | Function |
|---|---|
| SW[2:0] | variation rate S: 0 static, 1 → 5000, 2 → 1000, 3 → 224, 4 → 112, 5 → 28, 6 → 5, 7 → 1 |
| SW[5:3] | μ = 2^-(5+value) (value 7 → 2^-11) |
| SW[7:6] | Eb/N0 = 8 / 10 / 12 / 14 dB |
| SW[8] | channel: 0 primary (a 0.31–0.91), 1 control (a 0.20–0.60); changing it retrains |
| SW[9] | display 1 shows R1 instead of R2 |
| BTN0 | retrain with the switch settings (also leaves host mode) |
| BTN1 | clear counters |
| BTN3 | reset |
| Display 1 / display 0 | errors of R2 (or R1) / R3 per window of 2^20 tracking symbols (≈ BER in parts per million), refreshed every 0.17 s |
| LED[9:0] | switch positions; LED13 host mode, LED14 tracking, LED15 training |
| RGB0 | blue training, green tracking |
| RGB1 | R3 errors per window: green < 100, yellow 100–999, red ≥ 1000 |

Suggested demonstration (μ = 2^-8: SW[5:3] = 3; 10 dB: SW[7:6] = 1): step SW[2:0] from 1 (S = 5000) to 7 (S = 1). From the L5 sweep (`host/results/board_sweep_10dB_mu2-8.json`), per 2^20-symbol window: R2 stays at about 7500 errors at every rate (it cannot follow the channel); R3 stays near 380 for S ≥ 224 (RGB1 yellow), reaches about 670 at S = 28 and about 1500–1700 at S = 5 and 1 (RGB1 red) — the adaptive equalizer losing track while still beating R2. With μ = 2^-6 (SW[5:3] = 1) the loss happens at faster variation; with μ = 2^-10 (SW[5:3] = 5) at slower variation.

The seven-segment digit order and segment order (SEG[0..6] = a..g) follow the usual Boolean convention but are not stated in the Real Digital manual; if a display shows mirrored digits, the fix is the `an`/`font` mapping in `board_io.v`.
