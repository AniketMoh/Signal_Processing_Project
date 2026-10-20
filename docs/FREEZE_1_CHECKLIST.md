# FREEZE-1 checklist — for approval before the final sweep (20 Oct 2026, evening)

Status: **AWAITING APPROVAL.** The final sweep has not been started and final seeds 2000–2099 are unused. All numbers here are L1 pilot or L1 validation results. The LMS equations are unchanged (`lms_lib.lms_receivers`; recorded SHA-256 unchanged).

## 1. Fixed experimental definitions (approved earlier, unchanged)
- [x] Channel [1, a[n], 0.1], a = c·2⁻⁷. Training is static at c_lo, then the counter rises first. Three receivers on identical data. Supervised LMS, L = 16, Δ = 2.
- [x] Metrics: ε, ρ (trajectory baseline primary, literal c_lo baseline as sensitivity); S*_MSE at ρ_th = 0.5 (bands 0.25/0.75); S*_BER at f = 2 (bands 1.5/5); S_cross; N_rec (κ = 0.25, W = 64, post-transition reference).
- [x] Operating points: 16 dB primary (MSE/tracking), 14 dB secondary. Dashed 10⁻⁴ line on every L1 BER figure (D-12).

## 2. Grids, windows, seeds
| Item | Value | Status |
|---|---|---|
| μ, floating-point study | 2⁻⁵, 2⁻⁵·⁵, …, 2⁻¹¹·⁵ (14) | approved (P-13) |
| μ, FPGA comparisons | 2⁻⁵ … 2⁻¹¹ (7, a subset) | approved |
| S | 5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1 + static | approved |
| Window | whole triangle periods, N_eval = P·2(c_hi − c_lo)·S, each point uses its own bit count | approved |
| Final tracking seeds | 2000–2099 (100), static baselines with the same seeds (paired) | approved |
| 14 dB BER study seeds | 100000–101499 (1500) | approved (E-5) |
| Pilot / check / validation seeds | 1000–1099; 5000–5539; 300000–301999; 900000+ (all disjoint from the above) | — |

## 3. Final runs (what will be executed after approval)
| Run | Channel | Eb/N0 | μ | Seeds | Projected time* |
|---|---|---|---|---|---|
| Tracking sweep | primary 40–116, static nodes 40, 48, …, 112, 116 | 16, 14 | 14 values | 2000–2099 | about 10 min per SNR |
| Tracking sweep (control, E-4) | mild 26–77, nodes 26, 34, …, 74, 77 | 16, 14 | 14 | 2000–2099 | about 10 min per SNR |
| BER-resolution study | primary | 12 | 14 | 2000–2099 | about 10 min |
| BER-resolution study | primary | 14 | 2⁻⁷ … 2⁻¹¹·⁵ (10) | 100000–101499 | about 1–2 h |
| P2 abrupt transitions | large_up 40→116, mid_up 40→77, down 116→40 | 16, 14 | 2⁻⁷ … 2⁻¹⁰ | 2000–2099 | about 10 min |

*Projections from the measured pilot rate; confirmed on the first point of each run.

## 4. Corrections done since the audit (owner decisions E-1 … E-7)
- [x] **E-2 data collection.** `sweep.run_point_full` stores per-seed errors, per-seed bursts (gaps 10/20/40), bit counts and pairing metadata. **Regression test:** the new engine reproduces the stored grid-pilot numbers exactly (J3 equal to machine precision, error counts identical).
- [x] **E-1 statistics.** `sweep_analyse.py` v2 uses the paired seed-level bootstrap as the primary BER comparison where the reference has ≥ 100 expected errors in both the trajectory window and the static runs; otherwise the point is reference-limited. Plain Wilson and burst-adjusted Wilson are sensitivity columns only. **Validation:** §5.
- [x] **E-3 S_cross.** Per-S status A (advantage demonstrated) / L (loss confirmed) / ? (inconclusive). On the pilot data:
  - μ = 2⁻⁵ (16 and 14 dB): advantage demonstrated down to S = 5, confirmed loss at S = 2.
  - μ = 2⁻⁵·⁵ (16 dB): inconclusive at S = 1.
  - All smaller μ: "no S_cross observed within the grid".
- [x] **E-4 / E-5** in `freeze_grids.py`.
- [x] **E-6 P2 training.** `check_NT_p2.py`: N_T = 30000 fails for the "down" step at μ = 2⁻¹⁰ (frozen filter not converged: +1.45× the LMS excess at 16 dB, +0.61× at 14 dB). **N_T = 60000 passes all 16 cases** (2 training channels × 2 SNR × 4 μ). → **P2 uses a common N_T = 60000.** The continuous sweep keeps 30000 (its own check passed).
- [x] **E-7.** `PPR22_COMPARISON.md` rewritten with four labelled issues; register rows R-12 … R-20 added.
- [x] **A-1 log-linear interpolation** implemented: used where every static node has ≥ 1 error; linear is reported alongside.
- [x] **Exponent sensitivity** documented (7 predeclared variants):
  - 16 dB pilot: 0.519, systematic band 0.486–0.544;
  - 14 dB pilot: 0.525, band 0.493–0.550;
  - the seed-only interval (±0.001) is not the real uncertainty.

  Pilot conclusion (not final): consistent with ½, the 2/3 ramp exponent is outside the band.
- [x] **Re-analysis of the existing pilot data with v2 (no new simulation).** Every pilot S*_BER that was defined is unchanged: 16 dB μ = 2⁻⁵ → 5; 14 dB μ = 2⁻⁵ → 5, μ = 2⁻⁵·⁵ → 10. All other pilot BER statuses remain reference-limited, as expected with 20 seeds.

## 5. Validation of the paired bootstrap (E-1 requirement)
Design (`validate_bootstrap_run.py`, `validate_bootstrap_analyse.py`, log `results/validate_bootstrap_log.txt`):
- 2000 new seeds (300000–301999) split into **40 independent replicate experiments of 50 seeds**, at 12 dB on the primary channel.
- Configurations: μ ∈ {2⁻⁵, 2⁻⁸} × S ∈ {20, 1000}, each with its own 11 paired static nodes.
- "Truth" is the value pooled over all 2000 seeds. Each replicate is analysed exactly as the final data will be: the interpolation method is chosen from its own data, and B = 2000 resamples are used.

| Configuration | True ratio BER_R3/BER_ref | Paired-bootstrap coverage (nominal 95 %) | Bootstrap SD / actual spread | R3-only coverage: plain Wilson / burst Wilson / seed bootstrap |
|---|---|---|---|---|
| μ = 2⁻⁵, S = 20 (bursts 1.86) | 1.04 | 36/40 | 0.96 | 33/40 / 37/40 / 37/40 (SD ratio 0.61 / 0.84 / 0.88) |
| μ = 2⁻⁵, S = 1000 | 1.005 | 40/40 | 0.97 | 36/40 / 38/40 / 38/40 (0.75 / 1.02 / 1.09) |
| μ = 2⁻⁸, S = 20 (bursts 1.16) | 4.75 | 36/40 | 1.09 | 38/40 / 38/40 / 38/40 (0.90 / 0.97 / 0.99) |
| μ = 2⁻⁸, S = 1000 | 1.02 | 36/40 | 0.88 | 38/40 / 38/40 / 37/40 (0.85 / 0.91 / 0.92) |

What this shows (L1 validation):
1. **The paired bootstrap gets the size of the uncertainty right.** Its standard deviation is 0.88–1.09 of the real replicate-to-replicate spread.
2. **Coverage is close to nominal.** Overall 148/160 = 92.5 %, which is statistically consistent with 95 % (exact 95 % interval about 87–96 %). It is slightly low, as percentile bootstraps tend to be with 50 seeds; the final run has 100 seeds.
3. **Plain Wilson is too narrow when bursts are large** (SD ratio 0.61, coverage 33/40). This confirms B-1. Burst-adjusted Wilson repairs most of it (0.84–1.02).
4. **Pairing helps.** Per-seed trajectory and reference errors are positively correlated (+0.18 to +0.52), so pairing reduces the noise of the ratio.
5. **The trajectory reference is right in the slow limit.** At S = 1000 the true ratio is 1.00–1.02, so with no tracking loss R3 matches its reference. At S = 20, μ = 2⁻⁸ the ratio is 4.75, a clear BER fail.
6. **Caveats:**
   - At 12 dB and small μ a 50-seed replicate sometimes has a static node with zero errors, so linear interpolation was used (27/40 replicates at μ = 2⁻⁸). Linear gives a 4–7 % lower ratio than log. With 100 seeds this happens less often, and both values are reported.
   - The "truth" includes each replicate's own seeds (1/40 of the pool), which flatters coverage slightly.
   - Recommendation: accept the method as the primary evidence and quote the observed 92.5 % coverage in the report.

## 6. P5 and P6 before 25 October — concrete plan

### P5 — recorded-audio demonstration (PPR-22 Sec. 7.2)
- **Input:** your recorded mono clip, 5–10 s, any format (WAV preferred). If none arrives by 22 Oct, a clearly labelled synthetic placeholder is used.
- **Coding:** resample to 8 kHz, 8-bit PCM, MSB first, giving 64 kbit/s (a 10 s clip is 640,000 payload bits). Training uses the same 30000-symbol PRBS.
- **Runs (L1, same seed for all receivers):**
  - Eb/N0 = 14 dB, μ = 2⁻⁸ (a power of two, FPGA-relevant).
  - Channel: static S0; slow (S = 1000); near the measured boundary for that μ (taken from the final S*_MSE); fast (S = 1).
- **Outputs:**
  - per scenario four WAV files: original, R1, R2, R3;
  - BER per receiver;
  - waveform SNR against the original;
  - per-bit-plane error counts;
  - one figure: waveform, error positions in time and the channel trajectory underneath.
- **Code:** a new `audio_demo.py` with a helper that feeds given payload bits through the same link (no change to the LMS or the channel code).
- **Time:** about half a day (23 Oct).

### P6a — fixed-point software model (PPR-22 Sec. 6, the part feasible before 25 Oct)
Same LMS equation, finite-precision arithmetic. This is the L2 model the RTL will be checked against.

| Element | Proposed default (needs your approval) |
|---|---|
| Received sample r | 16-bit signed Q3.12, round to nearest, saturating |
| Channel taps | a exact in Q1.7 (2⁻⁷ steps); 0.1 in Q1.14 (nearest) |
| Noise | FPGA-compatible: sum of 12 uniforms from 12 LFSRs with distinct primitive polynomials and seeds, scaled by σ; Gaussian kept as reference |
| Coefficient accumulator B_acc | Q2.(B_acc−2), B_acc ∈ {16, 20, 24, 28, 32}, saturating |
| Multiplier coefficient B_mul | the B_mul most significant bits of the accumulator, B_mul ∈ {8, 12, 16}, round to nearest (truncation as sensitivity) |
| Products, adder tree | full precision (no intermediate rounding); output y and error e rounded to Q3.12 |
| Update | μ·e·u_k by arithmetic shift, rounded to the accumulator LSB (round to nearest; truncation as sensitivity) |

Tests (predeclared):
- **T1 equivalence.** With very wide words (B_acc = 40, B_mul = 24) L2 matches L1 within 10⁻⁶ in MSE.
- **T2 static convergence.** For every (B_mul, B_acc), steady-state MSE against the float result.
- **T3 update underflow.** Measured stall or bias onset against the prediction |μ·e·u| < LSB/2.
- **T4 tracking.** S*_MSE at μ ∈ {2⁻⁶, 2⁻⁸, 2⁻¹⁰} for B_acc ∈ {16, 20, 24} on a reduced S grid around the float boundary.
- **T5 hardware noise.** The LFSR noise generator validated by mean, variance, autocorrelation, tail and BER effect (PPR-22 Sec. 4.3).
- **T6 RTL vectors.** Reference vectors exported for P8.

Deferred to the final phase (stated in the midterm report):
- the full (μ, S, B) surface;
- resource numbers;
- the 8/12/16-bit synthesis (P9).

Time: about 1.5 days (21–22 Oct), running while the final L1 runs execute.

### Day plan
| Day | Work |
|---|---|
| 21 Oct | Approve this checklist → final L1 runs start (about 1 h, plus the 14 dB study in the background); P6a T1/T2 |
| 22 Oct | Final analysis and figures (BER, MSE, ρ, S*, μ_opt with exponent band, N_rec, coefficient trajectories); P6a T3–T5 |
| 23 Oct | P5 audio; P6a T6; plain-language notes for every stage |
| 24 Oct | Midterm report (register of changes, levels L1/L2, four labelled issues, deferred items) |
| 25 Oct | Final checks and submission |

If time runs short, the order of what is cut is: T6 vectors, then T4 (reduced to one μ), then extra figures. The final L1 results and P5 are never cut.

## 7. Items needing your decision now
1. **Approve this FREEZE-1 configuration** (sections 1–4, including P2 with N_T = 60000 and the control channel).
2. **Accept the bootstrap validation** in section 5 as adequate for using the paired bootstrap as primary evidence.
3. **Approve the P6a defaults** in section 6, or edit the word-length grid and rounding modes.
4. **Send the audio clip** for P5 (or confirm the synthetic placeholder).

Can wait until after the sweep: non-minimum-phase P1 test, triangle-vs-sinusoid check, decision-directed mode, MathWorks cross-check, image result.
