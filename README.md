# Signal Processing Project

**FPGA-Based LMS Tracking of Time-Varying ISI Channels: How Fast Can a Channel Change Before a Fixed-Point Equalizer Loses It?**

EE2000 (Signal Processing) course project, IIT Hyderabad, team 22.
Mid-term report (mtr-22) submitted 25 Oct 2026; final report due 15 Nov 2026; presentation 20 Nov 2026.

An LMS equaliser tracks a time-varying intersymbol-interference channel. Three receivers are compared on every run:
R1 (no equaliser), R2 (equaliser frozen after training) and R3 (adaptive LMS). The project finds how many symbols per
channel step (S) the adaptive equaliser needs at each step size μ, first in floating point (L1) and fixed point (L2),
then in RTL (L3), in Vivado (L4) and measured on a Real Digital Boolean Board (Spartan-7, L5).

## Where to start

| You want | Go to |
|---|---|
| The mid-term report | [`midterm_mtr-22/mtr-22.pdf`](midterm_mtr-22/mtr-22.pdf) |
| The final report source | [`final_report/main.tex`](final_report/main.tex) (FPGA, board confirmation and live demo: [`s_fpga.tex`](final_report/s_fpga.tex)) |
| FPGA design, how to build and program the board | [`fpga/README.md`](fpga/README.md) |
| Board results (L3–L5) | [`fpga/FPGA_RESULTS.md`](fpga/FPGA_RESULTS.md) |
| Board re-measurement of the mid-term findings | [`fpga/host/results/confirm/CONFIRMATION_REPORT.md`](fpga/host/results/confirm/CONFIRMATION_REPORT.md) |
| Viva / demo cheat sheet | [`fpga/VIVA_CHEATSHEET.md`](fpga/VIVA_CHEATSHEET.md) |
| Simulation code and results of the mid-term, by phase | [`midterm_mtr-22/README.txt`](midterm_mtr-22/README.txt) |
| Project specification and decision log | [`docs/`](docs/) |

## Layout

| Path | Contents |
|---|---|
| `reference/` | Preliminary report (PPR-22) and the course project description |
| `docs/` | Specification, decision log (findings F-1 … F-7), audit, stage notes, misadjustment derivation, L1/L2 results |
| `figs/` | Plots from the L1 and L2 stages (see `figs/README.md`) |
| `midterm_mtr-22/` | Mid-term report PDF, its LaTeX source, and all simulation code and results grouped by phase |
| `fpga/rtl/`, `fpga/sim/` | Synthesisable RTL and the bit-exact regressions against the L2 model |
| `fpga/vivado/` | Build and programming scripts, timing/utilisation reports, ready bitstreams |
| `fpga/host/` | PC scripts for the board: sweeps, payloads (image, recorded and live audio), live dashboards, board confirmation |
| `final_report/` | LaTeX source and figures of the final report |

## Validation levels

L1 floating-point simulation · L2 fixed-point simulation · L3 RTL simulation · L4 Vivado synthesis/implementation · L5 board measurement.
Every result in the reports states its level.

## Branches and tags

- `main` — the complete project (this branch).
- `fpga-implementation` — working branch for the FPGA stage; merged into `main`.
- Tags mark the milestones: `midterm-mtr22` (mid-term submission), `fpga-board-confirmed` (board re-measurement and live demo).

The underwater/real-world application extension of the submitted final report is developed separately and is not part of this branch.

## Not in the repository

A copyrighted song used once as a custom audio payload (`fpga/host/results/payload/custom_*`) is kept out of git on purpose.
