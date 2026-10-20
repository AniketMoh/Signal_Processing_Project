# PROJECT_SPEC.md — v1.2 (20 Oct 2026)

Shared source of truth = master prompt v1.0 and the preliminary report PPR-22, amended **only** by the entries in DECISIONS.md. This file restates the changed items in full. Sections not listed here are unchanged from master prompt v1.0.

Research question (unchanged): **How rapidly can a time-varying ISI channel change before a fixed-point LMS equalizer loses tracking, and how do LMS step size, coefficient precision and FPGA hardware constraints affect this limit?**
Three-receiver architecture (R1 direct, R2 frozen LMS, R3 adaptive LMS on the identical impaired stream) and the full project scope are preserved.

Validation levels: L1 float sim · L2 fixed-point sim · L3 RTL sim · L4 Vivado · L5 board. Numbers in this file are L1-analytic pilot values unless stated; they are not final results.

## 1. What changed relative to v1.1 and PPR-22

| Item | Now | Decision |
|---|---|---|
| Tracking metrics | **BER and MSE are both headline metrics.** BER boundary S\*_BER (PPR-22 criterion kept), MSE boundary S\*_MSE (oracle-normalized, additional). Reported separately, never merged | D-02 |
| Step-size theory | sqrt law kept as random-walk reference; 2/3 as conditional alternative; exponent measured | D-01 |
| Channels | mild control kept; primary candidate a in [0.3125, 0.90625], provisional | D-03 |
| Working parameters | L = 16, pilot Eb/N0 = 14 and 16 dB, Delta_a = 2^-7 | D-07 |
| Eb/N0 | relative to transmitted symbol energy | D-08 |
| N_rec | post-transition steady state, sustained | D-09 |
| Corrections | PRBS, saturation, underflow, Doppler wording, B_acc/B_mul | D-10, D-04 |

## 2. Experiment schedule
- n = 0 … N_T−1: channel static at a_lo; R2 and R3 are the same filter, trained on the PRBS (x^15 + x^14 + 1, period 32767, seed 1, N_T = 30000).
- n = N_T: R2 frozen (w_F = w[N_T]); variation starts; R3 continues (supervised evaluation unless stated).
- Variation: triangle, counter step Delta_a = 2^-7 every S symbols, **start phase a_lo, direction upward**. Period = 2 × (counter range) × S: primary 152·S, mild 102·S symbols.
- Evaluation window n in [N_T, N_T + N_eval), N_eval = 152,000 (one full primary period at S = 1000; many periods at small S). Window length and number of periods are reported with every result.
- Abrupt experiment: static h_A until N_C > N_T, then h_B.
- Identical bits, trajectory, noise and training sequence for R1/R2/R3 and across all parameter points (seeds derived from the experiment seed only). Pilot seeds 1000–1099, final seeds 2000–2099.

## 3. Definitions
Notation: u[n] = [r[n] … r[n−L+1]]^T, y = w^T u, e[n] = x[n−Delta] − y[n] (a-priori error). L and Delta are identical for R2, R3 and the oracle.

**Eb/N0 (D-08).** x = ±1, Eb = 1, noise variance per real sample sigma^2 = 1/(2 Eb/N0). Flat-channel BER = Q(sqrt(2 Eb/N0)).

**BER (headline).** Per receiver, aligned: R1 by the dominant-tap index (0), R2/R3 by Delta. BER vs S for R1, R2, R3 on identical data.
- **S\*_BER** (PPR-22 criterion, details P-10): fastest S with BER_R3(S) <= f × max(BER_R3,static, BER_floor); f = 2 provisional, BER_floor = 3/N_bits.
- **S_cross** (PPR-22 Sec. 3.1, only if it exists): smallest S at which R3 still has significantly lower BER than R1 and R2.

**MSE (headline).** J_R2(S), J_R3(S) = mean e² over the evaluation window and seeds, plus windowed MSE vs time around abrupt transitions.

**Instantaneous-channel oracle (analysis tool, never a fourth hardware receiver).** For each n build the L×(L+M−1) matrix H[n] whose row j uses the taps that were actually active at time n−j, so **coefficient changes inside the observation window are included**. With white unit-power x and noise variance sigma^2:
- w_or[n] = (H H^T + sigma^2 I)^-1 H e_Delta
- J_or[n] = 1 − e_Delta^T H^T (H H^T + sigma^2 I)^-1 H e_Delta

This is the minimum MSE of any L-tap linear equalizer that knows the channel. A quasi-static version (all rows use the taps at time n) is kept only for comparison. Near-zero guard: denominators use max(J_or, J_floor), J_floor = 1e-3 (the working SNR keeps J_or well above it).

**Oracle-normalized excess MSE (additional).**
- eps(mu, S) = (J_R3 − J_or) / max(J_or, J_floor), with J_or averaged over the same window.
- **Static-baseline subtraction:** eps_static(mu) is the same quantity on the static S0 run with the same mu (it is the LMS misadjustment, not tracking loss). Only the part above it is attributed to tracking.
- eps_plateau: excess MSE of the best single fixed filter for the time-averaged channel (computed analytically). It is the level R3 can fall back to once it can no longer follow the channel.
- rho = (eps − eps_static(mu)) / (eps_plateau − eps_static(mu)): 0 = no tracking loss, 1 = no better than a fixed averaged filter.
- A grid point passes if its 95 % bootstrap interval over seeds lies below rho_th and fails if it lies above; otherwise it is indeterminate (counted as not passing). **rho_th = 0.5 provisionally**; the final value is determined on pilot seeds and frozen at FREEZE-1. S\*_MSE is reported for rho_th in {0.25, 0.5, 0.75} as a sensitivity band.
- **S\*_MSE** = smallest passing S, only if the passing region is monotonic (once a point fails every faster point fails or is indeterminate). Otherwise S\*_MSE is undefined and the passing set and first failing S are reported. "No point fails within the S grid" is a valid outcome.
- If S\*_BER and S\*_MSE disagree, both are reported with an explanation.

**Reacquisition (D-09).** N_rec = smallest k such that the seed-averaged moving-average MSE (window W = 64) stays within (1 + kappa), kappa = 0.25, of the post-transition steady-state MSE for all n >= N_C + k. Reported versus mu.

**mu_opt study (D-01).** mu_opt(S) = argmin over the mu grid of the chosen metric (eps and also BER), with parabolic refinement in log mu. Fit log mu_opt vs log(Delta_a/S) with a confidence interval; compare with 1/2 and 2/3.

**Precision (L2, D-04).** B_acc swept with B_mul fixed; B_mul swept with B_acc non-limiting. Underflow indicator: fraction of updates that quantise to zero and divergence of the fixed-point coefficient trajectory from the float one.

## 4. Channels
**Control:** h = [1, a, 0.1], a = c × 2^-7, c from 26 to 77 (0.2031 … 0.6016). Minimum phase, open eye.
**Primary candidate (provisional, not frozen):** same form, c from 40 to 116 (0.3125 … 0.90625). Minimum phase (the zero reaches the unit circle only at a = 1.1); eye margin 1 − (a + 0.1) goes from 0.59 to about 0 at the top.

**L1-analytic pilot at L = 16** (quasi-static oracle, time average over the trajectory, one fixed Delta per row; `code/pilot_analytic.py`):

| Channel | Eb/N0 | J_or (mean) | eps_plateau | eps frozen at a_lo | cond(R) max | min abs H | R1 BER at a_lo / a_hi (exact) |
|---|---|---|---|---|---|---|---|
| Control | 14 dB | 0.0230 | 0.60 | 2.25 | 10.4 | 0.498 | 9.8e-8 / 4.4e-3 |
| Control | 16 dB | 0.0147 | 0.98 | 3.61 | 10.6 | 0.498 | 6.3e-11 / 9.7e-4 |
| Candidate [0.50, 0.90] | 14 dB | 0.0332 | 0.52 | 1.77 | 48.7 | 0.202 | 5.8e-4 / 0.14 |
| Candidate [0.50, 0.90] | 16 dB | 0.0217 | 0.85 | 2.84 | 53.5 | 0.202 | 4.5e-5 / 0.13 |
| **Primary [0.31, 0.91]** | 14 dB | 0.0301 | 1.13 | 3.90 | 50.9 | 0.194 | 3.9e-6 / 0.15 |
| **Primary [0.31, 0.91]** | 16 dB | 0.0196 | 1.83 | 6.20 | 56.0 | 0.194 | 2.0e-8 / 0.14 |

The L = 11 numbers in v1.1 are superseded. The best Delta is flat for L = 16 (a fixed Delta costs under 0.01 % of mean oracle MSE), so Delta is decided in P1 by the delay sweep.
Observations to carry forward: (i) the control channel shows a large MSE penalty for a frozen filter (excess 2.3–3.6) although its BER stays tiny, which is why BER and MSE must both be reported; (ii) the control's plateau is below or near 1, so MSE boundaries on it may be hard to resolve; (iii) condition number of R is about 50 on the harsher channels, so convergence is slow and N_T must be checked against the smallest mu.

**Pre-registered selection rule (LMS pilot, pilot seeds only).** Freeze the *mildest* candidate satisfying all of:
- C1 measurability: eps_plateau >= 1.0 at the working Eb/N0;
- C2 equalizable: cond(R) <= 70 over the trajectory and min |H(e^jw)| >= 0.15;
- C3 BER visibility: R1 BER at a_hi >= 10× R3 static BER, and R2 expected error count >= 100 within 10^7 bits at some S;
- C4 bracketing: for at least one mu, R3 passes at some S and fails at some faster S (at least two grid points each side), for the MSE criterion; the BER criterion is checked and reported separately.
Analytic status: primary meets C1 and C2 at both pilot SNRs; the candidate [0.50, 0.90] fails C1. **LMS pilot status (P3, 20 Oct, L1 pilot, finding F-6): only the primary channel satisfies C1–C4, at both 14 and 16 dB; the control fails C1 and C3b; candidate A fails C1.** The Eb/N0 for the final run is still to be chosen by the owner at FREEZE-1.

## 5. Precision and architecture
B_mul = bits of the coefficient entering the multiplier (MSBs of the accumulator). B_acc = accumulator bits in which updates are added. Q-formats, round-to-nearest vs truncation and saturation are explicit L2 parameters. First RTL: fully parallel datapath as in PPR-22 Table 3 (L multipliers each for R2 filtering, R3 filtering and the R3 update, about 51 DSP48E1 in total, an estimate until synthesis; the earlier time-multiplexed MAC proposal was withdrawn on 20 Oct, see D-05); verified at L3 by bit-exact comparison with L2 (which preserves the plain-LMS update order). DSP count is expected to be nearly flat across widths and LUT/FF/Fmax to carry the cost differences: an expectation to be measured at L4.

## 6. Validation tests (all must pass before any tracking claim)

| ID | Test | Pass criterion | Level |
|---|---|---|---|
| V0 | Reproducibility | Same seed gives identical arrays; different seeds differ; parameters logged | L1 |
| V1 | Noise generator | Mean, variance, autocorrelation, tail fraction, seed repeatability within statistical limits | L1 |
| V2 | Flat-channel BER vs Eb/N0 (12 points, ≥ 2e6 bits, ≥ 100 errors each) | All points inside the 99 % binomial interval of Q(sqrt(2Eb/N0)) (P-11); 95 % result reported per point | L1 |
| V2b | Static ISI | R3 BER well below R1 on static ISI; R1 matches the exact 4-pattern formula | L1 |
| V3 | Alignment | Cross-correlation peak at Delta (R2/R3) and 0 (R1); BER with a wrong offset ≈ 0.5 | L1 |
| V4a | Static LMS vs Wiener | Averaged LMS coefficients within 5 % of w_or | L1 |
| V4b | Excess MSE vs textbook formula | Within 20 % of mu·tr(R)/2 / (1 − mu·tr(R)/2). **Fails (factor 1.47–1.48, original record preserved), finding F-1: textbook assumes white residual error; ISI channel residual is correlated.** eps_static is measured, so the metric is unaffected | L1 |
| V4d | Reference misadjustment model (added 20 Oct, does not replace V4b) | Measured paired excess within 20 % of the exact first-order correlated-error model (fourth-moment algebra, no fitted parameter). **Passes** (1.055, 1.026, 1.011 at mu = 2^-8, 2^-9, 2^-10) | L1 |
| V4c | Pipeline control | White-input flat channel matches the formula within 5 %; excess proportional to mu | L1 |
| V5 | Delta sweep | MSE vs Delta curve measured; one Delta chosen; penalty reported | L1 |
| V6 | Training excitation | PRBS: period, balance, autocorrelation; PRBS reaches Wiener solution; alternating pattern fails (negative control) | L1 |
| V7 | Oracle | (a) Exact time-varying oracle agrees with a Monte-Carlo Wiener solution built from the system equation, within 2 %, on a fast ramp where it differs from the quasi-static oracle; (b) measured R2, R3 MSE never below J_or beyond statistical error; (c) static-run excess equals LMS misadjustment | L1 |
| V-M1 | Dynamic range | eps_plateau >= 1.0 at the working Eb/N0 | L1-analytic |
| V-M2 | Bracketing | For at least one mu, a passing and a failing S with at least two grid points on each side (pilot seeds); checked for both the MSE and the BER criterion | L1 |
| V-M3 | Frozen-vs-adaptive story | Some S where R2 fails and R3 passes; if none, reported as a finding | L1 |
| V-M4 | Statistical power | rho_th (and the BER threshold) separated from the S0 control by at least 5 seed standard deviations | L1 |
| V-M5 | Monotonicity and sensitivity | Passing set checked for monotonicity; S\*_MSE for three rho_th values, S\*_BER for three f values, two start phases | L1 |
| V8 | Reacquisition | N_rec stable across seeds | L1 |
| V9 | Underflow | L2 matches L1 with wide B_acc; zero-update fraction rises as B_acc narrows | L2 |
| V10 | Cycle budget | Cycles per symbol within budget; RTL bit-identical to L2 | L3 |

## 7. Required results (project decision) and status

| # | Result | Phase | Level | Status |
|---|---|---|---|---|
| 1 | BER vs variation rate, R1/R2/R3 | P3/P4 | L1 | P3 pilot done (L1 pilot, 20 seeds); final sweep pending FREEZE-1 |
| 2 | MSE vs variation rate, R2/R3 | P3/P4 | L1 | P3 pilot done (L1 pilot); final sweep pending FREEZE-1 |
| 3 | Oracle-normalized excess MSE vs variation rate | P4 | L1 | pilot curves done (eps, rho); final pending |
| 4 | Step size vs tracking performance (mu, S) | P4 | L1 | pilot S*(mu) and mu_opt preview done; final pending |
| 5 | MSE vs time around abrupt transitions | P2 | L1 | done (L1 pilot, 100 seeds): `fig_P2_mse_vs_time.png`, `fig_P2_ber_vs_time.png` |
| 6 | Reacquisition time vs step size | P2 | L1 | done (L1 pilot): `fig_P2_nrec_vs_mu.png`, F-5 |
| 7 | Coefficient trajectories vs the changing channel | P2/P3 | L1 | P2 part done: `fig_P2_coefficients.png`; P3 (continuous) trajectories pending |
| 8 | Fixed-point precision vs tracking capability | P6 | L2 | later |
| 9 | FPGA resources and timing | P9 | L4 | later |
| 10 | Original/direct/frozen/adaptive audio and image | P5 / final | L1 first | not started |

Items 1–7 are prioritised in floating point. No RTL work at the expense of the midterm experiments.

## 8. Midterm plan (due 25 Oct 2026)

| Date | Work |
|---|---|
| 20 Oct | Spec/decisions updated; analytic pilot at L = 16; P1 library and validation tests V0–V7 (**done: 11 of 12 checks pass, V4b fails, see F-1**); misadjustment investigation (**done: F-1 classified, V4d passes**) |
| 21 Oct | P1 finished and explained; P2 abrupt transition (results 5, 6, 7) (**done 20 Oct: F-4, F-5**) |
| 22 Oct | P3 continuous variation pilots (**done 20 Oct: F-6**); apply selection rule; commit FREEZE-1 (**needs approval of P-10, P-11, P-12 and the working Eb/N0**) |
| 23 Oct | P4 (mu, S) sweep on final seeds (results 1–4) |
| 24 Oct | P5 audio demonstration (synthetic placeholder unless a WAV is supplied); start of L2 if time allows |
| 25 Oct | Report, comments, authorship per member, submit |

## 9. Audio demonstration
Mono, 8 kHz, 8 bit. Until a recorded 5–10 s WAV is supplied a **synthetic placeholder** is used and labelled as such in every figure and file name. Same bits, trajectory and noise for all receivers. Reported: BER, waveform SNR against the original, the four audio files, S and mu. Described as communication-channel equalization, not acoustic noise cancellation. The Boolean Board audio output has a 50 Hz–5 kHz bandpass (manual); this is an output specification, not a microphone-input specification.

## 10. AI-use disclosure — draft (D-06)
"Generative AI tools (Claude and ChatGPT) assisted with literature review, algorithm and experiment design, code generation, debugging, verification planning, technical review of the design, and report preparation. [Include only after it is true:] AI-assisted code was reviewed, executed and tested by the team. All reported simulation results, synthesis statistics and hardware measurements were produced by running the code and tools; predictions and illustrative values are labelled as such. The team is responsible for understanding and defending all submitted work." Per-member authorship is recorded in the code headers (course requirement).

## 11. Explanation requirement
At every stage the delivery includes: what the code does in plain language; why the experiment is needed; the expected graph (prediction, written before the measurement) and what the measurement showed; what success means; what an unexpected result could mean; the concepts to know for the viva. Technical correctness is not traded for simplicity.

## 12. P1 status (20 Oct, L1, pilot seeds)
Code: `code/config.py`, `lms_lib.py`, `pilot_analytic.py`, `p1_validation.py`; outputs in `code/results/`. Checks V0, V1, V2, V2b, V3, V4a, V4c, V5, V6, V7a, V7b pass; V4b fails as pre-registered (F-1). Chosen Delta = 2 (provisional). N_T = 30000 is well above the measured convergence time. P2 (abrupt transition) is next.

Misadjustment investigation (20 Oct): `code/misadj_lib.py`, `code/investigate_misadjustment.py` (about 35 s), results in `code/results/misadjustment_*`. Outcome: the 1.48× factor is **not** an implementation or measurement problem (audit and 16-seed paired measurement); it is the textbook white-residual-error assumption failing on an ISI channel (lag-1 residual autocorrelation −0.53). The exact first-order correlated-error model reproduces the measurement (V4d passes) and the factor grows from 1.0 at a flat channel to 1.75 at a = 0.9. V4b remains a recorded failure. The project owner provisionally accepted the classification on 20 Oct; the explanation is regarded as "fully verified" only after review of `MISADJUSTMENT_DERIVATION.md`. Commands: `python3 p1_validation.py` and `python3 investigate_misadjustment.py` from `code/`.

## 13. Open items
1. Recorded audio WAV (P-08).
2. Configuration of the earlier 128×72 image experiment (4,911 / 6.661 % and 380 / 0.515 %) is undocumented; report only as an undocumented static-channel demonstration until reproduced.
3. FREEZE-1 values (22 Oct), including: working Eb/N0 (14 or 16 dB), rho_th, f, kappa, W, mu and S grids, N_T (F-4), static-baseline definition (P-12).
4. Approval of P-10, P-11, P-12 (exact wording in DECISIONS.md and `PROPOSALS_P10_P11_P12.md`).
5. Review of `MISADJUSTMENT_DERIVATION.md`.

## 14. P2 and P3 status (20 Oct, L1 pilot)
Code: `code/exp_lib.py`, `p2_abrupt.py`, `p2_nrec_noise_check.py`, `p3_run.py`, `p3_analyse.py`; outputs in `code/results/` (`p2_*`, `p3_*`, figures `fig_P2_*.png`, `fig_P3_*.png`). Setup in D-11; results in F-4 (training length), F-5 (abrupt transition) and F-6 (continuous pilot); plain-language explanation in `STAGE_P2_P3_NOTES.md`. All numbers are pilot results on pilot seeds (1000–1099 for P2, 1000–1019 for P3); none are final.


## 14a. Update 20 Oct (FREEZE-1 preparation)
Evaluation window rule (proposed P-13): N_eval(S)=P*2(c_hi-c_lo)*S, P=max(1,round(152000/(2(c_hi-c_lo)S))). Operating point 16 dB primary / 14 dB secondary; rho_th=0.5, f=2. Grids and BER plan: see FREEZE_1_PROPOSED.md (awaiting owner confirmation; final sweep not started).

(20 Oct, later) FREEZE-1 checks completed: N_T=30000 verified; window rule verified (exact lengths in FREEZE_1_PROPOSED.md); budget ~8-10 min per SNR; 12 dB static BER resolved; amendments A-1..A-3 proposed.

(20 Oct, later) Architecture decision: fully parallel datapath restored (D-05 reverted); no simulation affected.
