# Handoff — FPGA work (P7–P10), state on 8 Nov 2026

Read this first when continuing on another account. Final report + code due **13 Nov 2026**; viva on the Boolean Board (date TBD).

## 1. What is DONE and pushed (branch `fpga-implementation`, last commit `7434b5b`)

| Area | Where | Status |
|---|---|---|
| Synthesisable RTL (LMS core, front end, chain, run control, UART protocol, board I/O, demo mode) | `fpga/rtl/` | Done, verified |
| Bit-exact regressions vs the L2 Python model | `fpga/sim/run_*.py` | All pass |
| Vivado flow (XDC from Real Digital, build, OOC core, programming) | `fpga/vivado/` | Done; bitstreams in `fpga/vivado/bitstreams/` |
| Board L5 = L2 count for count (8 configs, B_acc 16 and 26) | `fpga/host/run_board.py verify` | Done |
| BER/MSE vs S sweeps on the board + figure | `fpga/host/results/` | Done |
| Word-length synthesis sweep (13 configs) | `fpga/vivado/reports/` | Done |
| Results write-up | `fpga/FPGA_RESULTS.md`, `fpga/README.md` | Done |
| Final report source with FPGA section §7, outdated mid-term text updated, AI disclosure | `final_report/` (compiles, 26 pages) | Done |

Mid-term source `midterm_mtr-22/` is untouched (teammates' submitted work). Responsible members per file: LMS core Pradeep Kumar; chain/run control Aniket Mohapatra; Vivado/XDC/top Bhavyam Shankar; UART/host/board I/O/payload Gautam Garg.

## 2. IN PROGRESS, NOT committed: audio / image / live-audio payloads over UART

Goal: send the P5 voice recording, the P5 image and live laptop-microphone audio through the real board; get R1/R2/R3 decisions back; reconstruct audio/images; check against L2; play a receiver on the board's audio jack.

### Design (implemented)
- UART raised to **1 Mbaud** (`CLKS_PER_BIT = 100`); host scripts use `BAUD = 1_000_000` with a 1 MB serial RX buffer.
- `'X'` frame flags: bit0 static, **bit1 payload from PC**, **bit2 play on board**. In payload mode every byte after the frame is payload (MSB first) + 1 padding byte; run ends at `n_total = N_T + 8*(n_bytes+1)` or 0.5 s after the last byte.
- `fpga/rtl/payload_io.v` (new): RX FIFO → bit serialiser; decision packer that removes receiver delays (R1 0, R2/R3 Δ=2) and emits one 24-bit word {R1,R2,R3 byte} per payload byte; TX FIFO; playback FIFO → 8 kHz → PWM on `left/right_audio_out` (pins N13/N14), receiver chosen by **SW[11:10]** (0 R3, 1 R2, 2 R1).
- `fpga/rtl/fifo_sync.v` (new): BRAM FIFO, **read data valid two clocks after the read request is registered** (this latency caused two bugs, both fixed).
- `exp_core.v`: payload source mux; pauses symbol generation (gates the noise LFSR) when the next payload bit is missing or the TX FIFO is nearly full — symbol sequence unchanged.
- `host_if.v`: payload mode, 0.5 s idle timeout, decision-word streaming before the report, version byte = 2, sticky 'I'/'Q', `arm` mask so a stale `done` does not end a new payload run.
- `top_boolean.v`, `boolean.xdc`, `build_top.tcl` updated; display window 2^16 symbols in payload mode; LED12 = payload mode; RGB0 red = audio playing.

### Verified so far
- Simulation: `fpga/sim/run_payload_test.py` → **ALL PASS** (decisions of all 3 receivers and counters identical to L2, playback samples = selected receiver, output-full pause exercised, back-to-back runs).
- Regressions still pass: `run_chain_syn_tests.py`, `run_top_test.py`, `run_lms_syn_tests.py`.
- Vivado build OK: 51 DSP, 5031 LUT, 4980 FF, 4 BRAM, WNS +0.482 ns. Bitstream at `fpga/vivado/build/top_m12_a16_r1/top_boolean.bit` (version 2; **not yet copied to `bitstreams/`**).
- Board: 1 Mbaud works; `run_board.py verify` still **ALL IDENTICAL** with the new build.

### Lost-byte bug: FIXED (8 Nov)
Symptom: in payload mode one PC->board byte was sometimes lost (often the first payload byte after the `'X'` frame).
How it was located: a new `'D'` command returns link counters (bytes received, framing errors, payload bytes accepted,
bytes dropped because the buffer was full); `fpga/host/diag_link.py` reads them around each trial. Every lost byte was a
**framing error** at the board's UART. The FPGA was cleared by experiment: 400 000 bytes with the board idle, computing and
transmitting, and 30 run starts followed immediately by bytes, all with 0 framing errors; a real-timing simulation (1 Mbaud)
was also clean.
**Root cause: the PC scripts.** `run_payload.stream()` and `diag_link.py` set `serial.timeout = 0.01` right after writing
the `'X'` frame. On Windows, pyserial applies a timeout change by reconfiguring the port (`SetCommState`), and the FTDI
re-applies its settings, which corrupted a byte still being transmitted.
**Fix:** `run_board.Board` opens the port once with `timeout=0.01` (its `read_exact` keeps its own deadline) and nothing
changes port settings during a transfer. Result: 0 of 30 diag runs short (before: 5/20 and 16/30); the image payload is
identical to L2 in all 11 scenarios.
Also kept (harmless, more robust): `uart_rx.v` now has a 40 ns glitch filter, a 3-sample majority vote and a framing-error
output; `host_if.v` has the `'D'` diagnostics command. Two stop bits from the PC were tried and are NOT needed (they did not help).

### Then finish
```
cd fpga/host
python run_payload.py image      # 11 scenarios, every byte checked vs L2, PNGs + image_metrics.json in results/payload/
python run_payload.py audio      # P5 voice, 4 scenarios (≈5 min, L2 check slow), WAVs + audio_metrics.json
python run_payload.py live --seconds 20 --S 28 --p 8 --ebn0 10 --pc-play R3   # microphone; board jack plays SW[11:10] receiver
```
Then: copy the new bitstream to `fpga/vivado/bitstreams/`, add the payload results to `FPGA_RESULTS.md`, `fpga/README.md` (SW[11:10], audio jack, 1 Mbaud) and a short subsection in `final_report/s_fpga.tex` (+ remove "not implemented: audio/image over UART" from `s_fpga.tex` Limits and `s7_conclusion.tex`), label live audio as a demonstration (not a measurement), commit and push.

## 3. Environment on this PC
- Vivado 2025.2 at `D:\2025.2\Vivado\bin` (has Spartan-7); iverilog in `C:\iverilog\bin`; MiKTeX pdflatex.
- Python 3.14 with numpy, scipy, **numba**, pyserial, matplotlib, **sounddevice**, **scikit-image** (installed during this work).
- Board: JTAG target `xc7s50_0`; USB-UART **COM8** (FTDI). After programming over JTAG the COM port can drop briefly — reopen (run_board.py retries).
- Program: `vivado -mode batch -nojournal -nolog -source fpga/vivado/program_board.tcl -tclargs <bitfile>`.

## 4. Still to do by the team (not technical)
- Look at the 7-segment displays during a demo (digit/segment order not checked by eye).
- Merge `fpga-implementation` into `main` when agreed.
- Shorten the abstract if wanted; each member reviews their files before the viva.
