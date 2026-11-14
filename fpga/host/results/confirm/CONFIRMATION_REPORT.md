# Mid-term findings re-measured on the Boolean Board

*14 Nov 2026. Level L5 (board) against the mid-term's L1 (floating-point) results. Supervised LMS throughout. Written with AI assistance (Claude), project decision D-06.*

## What was done

The mid-term's final P3/P4 tracking sweep was re-run on the FPGA, using the same frozen grid, rules and analysis code:
- **Grid** (FREEZE-1): 18 variation rates plus static; the 7 FPGA step sizes 2^-5 … 2^-11; N_T = 30000; whole triangle periods (about 152000 symbols); 11 (primary) or 8 (control) static baseline nodes; seeds 2000–2099.
- **Configurations:** primary channel at 16, 14 and 12 dB; control channel at 16 and 14 dB. All five use the 16-bit accumulator build (`m12_a16_r1`). Primary 16 dB was repeated with the 26-bit build (`m12_a26_r1`).
- **Volume:** 121,800 board runs, about 25 billion symbols.
- **Analysis:** the mid-term's own `sweep_analyse.analyse()`, unchanged, on the board data. The L1 data was restricted to the same 7 step sizes and seeds, for a like-for-like comparison.

Scripts are in `fpga/host/confirm/`; data, tables and figures are in `fpga/host/results/confirm/`.

| Script | What it does |
|---|---|
| `board_midterm_sweep.py` | runs the board sweep |
| `confirm_analyse.py` | S*, rho, mu_opt, S_cross: board vs L1 |
| `confirm_extras.py` | R1 floor, noise distribution, misadjustment, word length |
| `confirm_wordlength.py` | paired 16- vs 26-bit comparison |

Every run checked that the board evaluated exactly the expected number of symbols. The channel trajectory was checked against the L1 trajectory for every rate.

## Results: what the board confirms

| Mid-term finding | Mid-term (L1) | Board (L5) | Verdict |
|---|---|---|---|
| **Tracking boundary S*_MSE** (rho_th = 0.5), all 7 mu | table 3 | **identical in 42 of 42 cases** (6 configurations × 7 mu), including the "undefined" mu = 2^-5 at 12/14 dB and the 56 on the control channel at 14 dB | confirmed |
| **S*·mu ≈ 0.11 for mu ≤ 2^-8** | 28 / 56 / 112 / 224 | 28 / 56 / 112 / 224 (160 at 12 dB, as in L1) | confirmed |
| **R3 MSE at every (S, mu)** | – | board vs L1 median −0.1 … 0.0 %, extremes −0.3 … +1.0 % | confirmed |
| **Optimum step size grows with 1/S** (exponent, 7-mu grid) | L1: 0.476 / 0.493 / 0.457 / 0.561 / 0.540 | 0.487 / 0.489 / 0.454 / 0.557 / 0.538 (26-bit: 0.476) | confirmed |
| **Misadjustment 1.47× textbook** (control channel, a = 0.60, 14 dB) | 1.472 / 1.466 / 1.435 (paired 1.480 / 1.473 / 1.468) at 2^-8 / 2^-9 / 2^-10 | **1.481 / 1.471 / 1.467**; MSE 0.02920 / 0.02825 / 0.02780 vs 0.02919 / 0.02825 / 0.02779 | confirmed |
| **R1 error floor at a = 0.91** (P1: "14–20 %") | 14.10 / 15.06 / 16.28 % at 16 / 14 / 12 dB | **14.08 / 15.06 / 16.30 %** | confirmed |
| **R3 beats both controls down to S = 1 for mu ≤ 2^-6; loss only at mu = 2^-5, S ≤ 2** (primary channel) | same | same at 12, 14 and 16 dB | confirmed |
| **S*_BER** (f = 2), primary 12 dB | 2, 10, [28, 14], 56, 112, [320, 160], 500 | **identical** | confirmed |
| **16-bit accumulator preserves the boundary** (word length, P6) | L2 software result | identical S* for both builds. The paired MSE cost of 16 bits is < 0.02 % for mu ≥ 2^-9 and at most about 1 % (mu = 2^-11, slowly moving channel); R3 bit errors are equal within noise | confirmed on hardware |

## Where hardware and software differ, and why

1. **Bit error rates below about 10^-4 are lower on the board.**
   - **Cause:** the hardware noise is a sum of 12 uniform numbers (an Irwin–Hall distribution). It has the same variance as Gaussian noise but lighter tails, and it is bounded at ±6 sigma.
   - **Evidence:** its exact distribution predicts the board's R1 BER on static channels to within a few percent.

     | Primary, 16 dB | Gaussian | Sum of 12 uniforms | Board |
     |---|---|---|---|
     | a = 0.69 | 7.27e-3 | 7.17e-3 | **7.16e-3** |
     | a = 0.56 | 3.25e-4 | 2.41e-4 | **2.41e-4** |
     | a = 0.44 | 4.6e-6 | 0.97e-6 | **1.05e-6** |

     The mid-term predicted this limit ("below 1e-4 the planned 12-uniform hardware noise no longer approximates Gaussian BER"). It is now measured: 26 % fewer errors at 3e-4, about 5× fewer at 1e-6.
   - **Consequence:** at 14–16 dB, some S*_BER brackets differ by one grid step, and some points become reference-limited. The MSE results are unaffected, because the variance is identical.
2. **Lower mu_opt exponents than the mid-term's published 0.52 / 0.59.**
   - This is a grid effect, not the hardware: the hardware can only shift by whole bits, so it has no half-octave step sizes.
   - L1 restricted to the same 7 powers of two gives the same lower values as the board. The mid-term's 14-point grid resolves the optimum better.
3. **The 16-bit accumulator costs a little at the smallest step size.**
   - Up to 52 % of updates round to zero (stall) at mu = 2^-11.
   - Paired against the 26-bit build (same noise, same data), the MSE rises by at most about 1 %, and only at mu = 2^-11 on slowly moving channels (S = 224 … 2000). There the per-symbol tracking update is smallest, so the stalls swallow the slow drift.
   - It costs < 0.04 % on a static channel and < 0.03 % on fast channels.
   - This is the mechanism the mid-term described ("the required accumulator width grows as mu falls"), now measured. The boundary itself does not move.
4. **Apparent differences that are statistical artefacts:**
   - rho at mu = 2^-5, 14 dB (0.3 board vs 0.2 L1): the normalisation denominator is almost zero, and the mid-term marks this point "u";
   - "advantage over controls" on the control channel at 16 dB: almost no errors (fewer still with the lighter-tailed noise), so the test is inconclusive, not a loss.

## Not testable on this hardware (software-only results)

- **Reacquisition after abrupt channel steps (P2):** the RTL has no step channel.
- **Coefficient trajectories:** the weights are not read out.
- **Decision-directed and pilot-assisted modes:** the RTL is supervised only.
- **Half-octave step sizes:** shift-only mu.
- **Triangle vs sinusoid trajectory:** triangle only.
- **Exact BER below 1e-4 with Gaussian statistics:** the hardware noise is not Gaussian there.

## Figures

| Figure | Content |
|---|---|
| `fig_confirm_<config>.png` (6) | rho vs S for all 7 mu (board solid, L1 dashed); S*_MSE vs mu with the 0.11/mu law; mu_opt vs 1/S |
| `fig_wordlength_a16_vs_a26.png` | paired MSE cost of the 16-bit accumulator over (S, mu), and its stall fraction |
| `board_<config>_live.png` | snapshot of the live tracking curves (the first five runs) |

Tables: `confirm_summary_<config>.md`, `confirm_extras.md`, `wordlength_a16_vs_a26.md`. Mid-term analysis logs on the board data: `analysis_board_<config>_log.txt`.

## New bitstream `top_boolean_m12_a16_r1_sw12.bit` checked on the board (14 Nov, 03:45)

This bitstream adds the SW12 "static channel at maximum a" switch and the fix for the sym_idx wrap after 2^32 symbols.

- **`run_board.py verify`:** all 8 configurations are identical to L2, with the same counts as the standard build (report Table 8). Saved as `board_verify_m12_a16_r1_sw12.json`.
- **`run_board.py static-max`** (host mode, 10 dB, mu = 2^-8, 10^6 symbols each), identical to L2. Saved as `board_static_max_10dB_mu2-8_sw12.json`.

  | Static channel | R1 | R2 | R3 |
  |---|---|---|---|
  | a = 0.31 | 0.102 % | 0.000 % | 0.000 % |
  | a = 0.906 | **17.63 %** | 0.154 % | 0.237 % |

  On a channel that never moves, R3 is slightly worse than R2: adapting only adds gradient noise there.
- **Checked by eye (14 Nov, 16:40), demo mode, 10 dB, mu = 2^-8, S = 5000 (SW0, SW3, SW4, SW6 up):**
  - SW12 down: left (R3) 250–550, right (R2) 7000–9400, RGB0 green.
  - SW12 up: left 2500, right 1700, steady. Expected from the host test: about 2400 / 1500.
  - SW12 + SW9 up: right (R1) 9999.
  - SW12 down again: left 300, right 7400, green.
  - **SW12 works as designed.**
- **Board state left behind:** the standard `top_boolean_m12_a16_r1.bit` is loaded again, matching the Desktop "Program FPGA" shortcut.

## The 1500-seed 14 dB BER study on the board (14 Nov, 14:08–16:29)

The mid-term's study was repeated on the board with the same 1500 seeds (100000–101499), step sizes 2^-7 … 2^-11, all 18 variation rates and the 11 static nodes. That is 225,000 runs, analysed with the mid-term code. Results: `confirm_summary_primary_14_m12_a16_r1_ber14.md`, `fig_confirm_primary_14_m12_a16_r1_ber14.png`.

| mu | S*_MSE board / L1 | S*_BER board | S*_BER L1 (1500 seeds) |
|---|---|---|---|
| 2^-7 | 20 / 20 | bracket [56, 28] | 40 |
| 2^-8 | 28 / 28 | bracket [160, 80] | 112 |
| 2^-9 | 56 / 56 | bracket [320, 160] | bracket [320, 160] |
| 2^-10 | 112 / 112 | bracket [1000, 320] | bracket [1000, 320] |
| 2^-11 | 224 / 224 | bracket [2000, 500] | bracket [2000, 500] |

- **MSE:** every S*_MSE is identical. R3 MSE board vs L1: median +0.02 %, range −0.03 … +0.37 %.
- **mu_opt exponent:** 0.554 (board) vs 0.562 (L1, same 7 mu) vs 0.579 (mid-term, 14 mu).
- **BER:** identical brackets for mu ≤ 2^-9. At 2^-7 and 2^-8 the board leaves undecided the two points that L1 resolves (40 and 112). The board's brackets contain the L1 values.
- **Why:** the static reference makes 16–19 % fewer errors on the board (14828 vs 17620 node errors at 2^-7; 5096 vs 6299 at 2^-8), because of the lighter-tailed noise. Fewer reference errors make the moving-to-static ratio larger: 1.95 vs 1.81 at S = 40 (2^-7), 1.93 vs 1.66 at S = 112 (2^-8). With the paired bootstrap, the f = 2 test at that point becomes "?" (inconclusive) instead of passing.
- **The board was shared with the other chat:** it held the application bitstream (app1, version 3) when the run began. The standard bitstream was loaded for the run, and app1 was loaded again afterwards (16:32).

## Limits of this comparison

- Board and L1 use different random numbers for the same seed labels (LFSR vs numpy). The comparison is therefore statistical, not sample by sample. The 16- vs 26-bit comparison is paired.
- 100 seeds per point, as in the mid-term's final sweep.
- **The mid-term's 1500-seed 14 dB BER study** (mu 2^-7 … 2^-11, seeds 100000–101499, 225,000 runs) is done. A first attempt on 14 Nov at 02:21 was stopped by Claude Code because the laptop ran low on memory. The study was then re-run from 14:08 to 16:29 on the standard bitstream, saving after every point. See the section below.
- The 26-bit build is the 6 Nov version-1 bitstream (115200 baud). Its host protocol is identical for these runs.
