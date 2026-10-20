# DECISIONS.md — FPGA-Based LMS Tracking of Time-Varying ISI Channels

Baseline: preliminary report PPR-22 (the original proposal) and master prompt v1.0.
PPR-22 is not edited. Every place where this log refines or replaces one of its statements is listed in the register at the end, and the midterm report must reproduce that register.

Status keys: **APPROVED** · **PROVISIONAL** (approved to start work, to be validated and then frozen at FREEZE-1) · **PROPOSED** (needs approval) · **OPEN**.
Result level of numbers quoted here: L1-analytic pilot (closed-form calculations, no LMS run, no random data) unless stated. Nothing here is a final result.

Highest-priority rule (project decision, 20 Oct): preserve the research question, objectives and experimental commitments of PPR-22. Refinements must strengthen the project, not silently redefine it.

---

## Approved decisions

### D-01 — Step-size prediction  [APPROVED, amended 20 Oct]
- Retain the classical random-walk prediction mu_opt ∝ (variation rate)^(1/2) as a **theoretical reference** (Widrow et al. 1976; lag term ∝ 1/mu).
- Add the deterministic-ramp prediction mu_opt ∝ |v|^(2/3) (lag excess MSE ∝ v^T R^-1 v / mu^2) as a **conditional alternative hypothesis**. It holds only for a long steady ramp; a bounded triangle may never reach that regime.
- Measure the actual mu_opt versus variation rate and fit the exponent with a confidence interval. Neither exponent is assumed. Tracking error may saturate instead of growing without limit (bounded trajectory).
- Affects: sweep software, report Sec. 5.2/10.

### D-02 — Tracking metrics: BER and MSE both major  [APPROVED with amendments, 20 Oct]
This entry **supersedes my earlier version of D-02**, which made oracle-normalized MSE the primary criterion and BER secondary. That was an unapproved narrowing of PPR-22.
- **BER versus variation rate for R1, R2, R3 is a headline result.** The PPR-22 BER criterion (Sec. 5.7: the fastest preset at which R3 keeps BER within a stated factor of its static-channel value) is preserved and reported separately as **S\*_BER**.
- **MSE versus variation rate (R2, R3) is equally important**, plus MSE versus time around abrupt transitions.
- **Oracle-normalized excess MSE is an additional criterion**, giving **S\*_MSE**.
- If S\*_BER and S\*_MSE differ, both are reported and the difference is explained (MSE = loss of accurate adaptive tracking; BER = loss of reliable bit recovery). The two are never forced to agree and never both called "S\*".
- Oracle conditions: same L and Delta as R3; must model the channel coefficient changes **inside the equalizer observation window** (verified by test V7); normalization and static-baseline subtraction defined explicitly (PROJECT_SPEC.md Sec. 3).
- Threshold: 50 % of the dynamic range (rho_th = 0.5) provisionally; final value determined from **independent pilot seeds** and frozen at FREEZE-1.
- Measurability requirement retained; if no boundary can be identified this is reported honestly.
- PPR-22 Sec. 3.1 wording ("the boundary beyond which the adaptive receiver ceases to outperform its controls") is also kept, reported as **S_cross** if it exists (see P-10).

### D-03 — Channels  [APPROVED; primary channel PROVISIONAL]
- Original mild channel h = [1, a, 0.1], a in [0.2, 0.6], stays as the **baseline/control**. With Delta_a = 2^-7 the nearest counter limits are 26/128 to 77/128 (a = 0.2031 to 0.6016).
- Challenging **primary candidate**: a in [0.3125, 0.90625] (counters 40 to 116). Not frozen until it passes the pilot validation tests (spec Sec. 4, 6).
- Fixed conventions: static during training, R2 frozen at N_T, variation starts at N_T, starting phase a_lo, direction upward, Delta_a = 2^-7. Experiments are long enough to cover the relevant trajectories (N_eval = 152,000 symbols covers one full triangle period at S = 1000 for the primary channel; shorter S gives many periods).
- If the primary channel differs from PPR-22's example it is documented as a justified refinement (register R-5).
- Reason: for a <= 0.6 the peak ISI is 0.7 < 1, so the noiseless direct detector makes no errors.

### D-04 — Precision split into B_mul and B_acc  [APPROVED]
Independent experiments: B_acc swept with B_mul fixed, and B_mul swept with B_acc non-limiting. (Register R-8.)

### D-05 — FPGA architecture: fully parallel datapath as in PPR-22  [REVERTED 20 Oct by the project owner; supersedes the earlier time-multiplexed-MAC approval]
Decision: the FPGA datapath follows PPR-22 Sec. 6.5 / Table 3 and Fig. 1: a fully parallel L-tap structure (L multipliers for R2, L for R3 filtering, L for the R3 update, 3 for the channel FIR; about 51 DSP48E1 of 120, an unsynthesised estimate until L4). Plain LMS semantics are kept (y from w[n], then all taps updated with the same e[n]). The earlier proposal of one shared time-multiplexed MAC (about 3L + M + overhead cycles per symbol) is withdrawn and is not planned; it remains only a fallback if synthesis shows the parallel design does not fit or close timing. History: the time-multiplexed version was approved earlier and reverted on 20 Oct before any RTL work. **No simulation depends on this choice:** all L1 results (P1–P3, grid pilot, FREEZE-1 checks) model the algorithm, not the datapath, and the L2 model will use wide accumulators so that parallel and sequential summation give identical integers. Open risk to check at L4: the 16-term adder tree plus the update path against the 100 MHz clock; PPR-22 Sec. 6.3 states D = 0 is achievable at the UART symbol rate (many clock cycles per symbol, multicycle paths allowed), and Table 5 lists divided clock or delayed LMS as the contingency. (Register R-9, now: PPR-22 baseline restored.)

### D-06 — AI-use disclosure  [APPROVED]
Draft wording in spec Sec. 10; the review/testing sentences are used only once those steps are done.

### D-07 — Working parameters  [PROVISIONAL, project decision 20 Oct]
L = 16; pilot Eb/N0 = 14 dB and 16 dB; Delta_a = 2^-7; static training then controlled variation; fully parallel datapath for RTL (D-05, as in PPR-22). All are validated first and frozen at FREEZE-1.
Earlier pilot numbers computed with L = 11 are superseded by the L = 16 numbers in the spec.

### D-08 — P-01 Eb/N0 definition  [APPROVED]
Eb/N0 relative to transmitted BPSK symbol energy (x = ±1, Eb = 1): noise variance per real sample sigma^2 = 1/(2·Eb/N0), so a flat channel gives BER = Q(sqrt(2·Eb/N0)). Noise scaling is implemented in one function (`sigma_from_ebn0`) and checked by test V2. R1, R2, R3 always receive identical bits, trajectory and noise (seeds derived only from the experiment seed).

### D-09 — P-04 Reacquisition criterion  [APPROVED]
Reacquisition is measured against the **post-transition** steady-state MSE (measured from a long static run on h_B with the same mu), not only the pre-transition value: h_A and h_B have different oracle MSE, so the pre-transition level may be unreachable or too easy. Recovery must be **sustained**: N_rec = smallest k such that the seed-averaged moving-average MSE (window W = 64 symbols) stays within (1 + kappa) of that level for all n >= N_C + k. kappa = 0.25 and W = 64 are provisional and are fixed before the final abrupt experiment (FREEZE-1). Reported as a refinement of the PPR-22 criterion (R-4).

### D-10 — P-05 Editorial and technical corrections  [APPROVED]
1. Random-walk square-root prediction kept as reference; 2/3 ramp scaling added as conditional alternative; exponent measured (D-01).
2. Tracking error may saturate rather than grow without bound.
3. Sec. 5.4 of PPR-22: a PRBS makes the **transmitted symbols** white, but the correlation matrix of the equalizer input is R ≈ H H^T + sigma^2 I, which depends on the channel. It is not proportional to the identity. A PRBS is still the best simple excitation, and its period (32767) must be much longer than L.
4. B split into B_acc (accumulator) and B_mul (multiplier), see D-04.
5. Underflow wording: the update is lost when |mu·e·u| < LSB/2 under round-to-nearest (truncation gives a bias instead of a stall); whether adaptation stalls, drifts or is biased depends on rounding, accumulator width and the error statistics. "Grows without bound" is removed.
6. Deterministic triangular variation is described as a laboratory model of channel variation, **not** a physically accurate Doppler spectrum.
7. PPR-22 Sec. 6.3 "10^4 symbols/s" is corrected after checking the UART arithmetic (about 92 ksym/s at 115200 baud 8N1 if each byte carries 8 bits); D = 0 is unaffected.

### D-11 — P2 abrupt-transition setup  [PROVISIONAL, fixed at FREEZE-1 for the final run]
Static training of N_T = 30000 symbols on channel A (PRBS), R2 frozen at N_T, R3 continues supervised adaptation; the abrupt transition A -> B occurs at N_C = N_T + 20000 = 50000 (all receivers and the oracle see the same instant); N_post = 100000 symbols after N_C. Steps: **large_up** c 40 -> 116 (a 0.3125 -> 0.9063), **mid_up** c 40 -> 77 (0.3125 -> 0.6016), **down** c 116 -> 40. mu in {2^-7, 2^-8, 2^-9, 2^-10}; Eb/N0 = 14 dB; L = 16; Delta = 2; 100 pilot seeds (1000–1099); coefficient history every 16 symbols. Reference level for reacquisition (D-09): steady-state a-priori MSE of a static run on channel B with the same mu (20 seeds, last 200000 of 300000 symbols). N_rec uses the trailing 64-symbol moving average of the seed-mean e^2 (window ending at N_C + k), kappa = 0.25, 95 % percentile bootstrap over seeds (200 resamples). Predictions (never fitted): analytic frozen-filter MSE 1 − 2 w_A^T p_B + w_A^T R_B w_A; mean-weight transient J(n) = J_ss + Σ_i λ_i (q_i^T (w_A − w_B))² (1 − μ λ_i)^(2k), k = n − (N_C + L − 1).

---

## Gate: FREEZE-1 (pre-registration)  [PROPOSED procedure, required by D-02/D-03]
Before any final sweep: commit `FREEZE_1.md` containing primary channel (range, increment, phase, direction), working Eb/N0, L, Delta, N_T, mu grid, S grid, rho_th, BER factor f, BER floor, N_rec tolerance and window, seed sets, evaluation length. Pilot seeds 1000–1099 and final seeds 2000–2099 are disjoint. Anything changed afterwards is logged here and the affected results are rerun. Target: **22 Oct 2026**.

## Proposed items still open

### P-10 — BER criteria (S*_BER and S_cross)  [PROPOSED — exact wording submitted 20 Oct for final approval]

**Proposed text.**

1. *Evaluation.* For every (μ, S) grid point the pooled R3 bit-error count over all seeds and the whole evaluation window is used. N_bits = (number of seeds) × N_eval. R1, R2 and R3 are counted on identical data.
2. *Static reference.* BER_ref is the static-channel BER of R3 with the same μ, defined in P-12 (the baseline definition is the same one used for the MSE criterion).
3. *Pass/fail of a grid point.* Let T(f) = f × max(BER_ref, 3 / N_bits) (the "rule of three" floor makes the criterion meaningful when the static error count is zero). The point **passes** if the upper end of the 95 % Wilson interval of the pooled R3 BER is ≤ T(f); it **fails** if the lower end is > T(f); otherwise it is **indeterminate** and counts as not passing.
4. *S*\*_BER.* S*_BER is the smallest S in the grid that passes, **only if** the passing set is monotonic (once a point fails, every faster point fails or is indeterminate). If not monotonic, the passing set and the first failing S are reported and S*_BER is stated as undefined. "No point fails within the S grid" and "fails already at the slowest S" are valid outcomes and are reported as such.
5. *Factor f.* f = 2 is the primary value; f ∈ {1.5, 2, 5} is reported as a sensitivity band. f is fixed at FREEZE-1 from pilot data.
6. *S_cross (PPR-22 Sec. 3.1 wording).* S_cross is the smallest S in the grid at which the pooled BER of R3 is lower than that of **both** R1 and R2 by a one-sided two-proportion z-test at the 5 % level. It is reported only if R3 stops outperforming at some grid point; if R3 still outperforms R1 and R2 at the fastest S of the grid, the report states "no S_cross observed within the grid" (it is not set equal to the fastest S).
7. S*_BER and S*_MSE are reported separately; if they differ the report explains the difference. All parameters (f, floor, test levels, grids) are fixed at FREEZE-1.

**Why it is proposed (evidence).** The factor and the zero-error case were never stated in PPR-22. In the pilot (primary channel) the literal static run has zero errors, so the floor is the reference; with the literal reference R3 "fails" the criterion at slow S for several μ even though the BER is of order 10⁻⁶ to 10⁻⁵, because the trajectory visits harder channels than the static reference does (P-12). In the pilot R3 stays better than R1 and R2 at every grid point (S_cross not observed) while the MSE-based boundary exists.

### P-11 — Wording of validation test V2  [PROPOSED — exact wording submitted 20 Oct for final approval]

**Proposed text.** *Test V2 measures the BER of the direct detector on a flat channel (no ISI) at 12 Eb/N0 points from 0 to 8.25 dB, with 2 × 10⁶ bits per point and at least 100 observed errors per point. For each point the exact (Clopper–Pearson) 95 % and 99 % two-sided binomial intervals of the measured BER are computed and compared with Q(√(2 Eb/N0)). The 95 % result is reported for every point. V2 passes if the theoretical value lies inside the 99 % interval at all 12 points. A failing run is repeated once with different seeds before any conclusion is drawn; a systematic deviation (same sign at several points) is treated as a failure irrespective of the intervals.*

**Why it is proposed.** If the simulator were perfectly correct, requiring all 12 points inside the 95 % interval would fail 1 − 0.95¹² = 46 % of the time and the 99 % version 1 − 0.99¹² = 11 % of the time, so a single excursion is not evidence of a fault. Observed (pilot): 11/12 inside 95 %, 12/12 inside 99 %, minimum 247 errors per point (the project spec's earlier text said "within the 95 % interval at each point").

### P-12 — Definition of the static baseline for eps_static and BER_ref  [PROPOSED — new, found in the P3 pilot]

**Problem.** The spec says eps_static(μ) is measured "on the static S0 run with the same μ" and BER_static is the static BER, but does not say **which channel value** the static run uses. This matters because the LMS misadjustment grows with the coefficient a (finding F-1: static excess 4.3 % at a = 0.31 against 11 % at a = 0.91 for μ = 2⁻⁸). A static run at the starting value c_lo understates the baseline of a trajectory that visits larger a, and the difference is wrongly counted as tracking loss.

**Proposed text.**
- *Static baseline, MSE:* eps_static(μ; trajectory) = [ mean over the evaluation window of (J_static(c(n), μ) − J_min(c(n))) ] / J_or,mean, where J_static(c, μ) is the measured steady-state R3 MSE of LMS on a **static** channel with counter value c (7 values of c spanning the trajectory, 20 seeds each, linear interpolation in c) and c(n) is the actual counter trajectory of the grid point. This is the S → ∞ limit of the same trajectory. The literal reading (static run at c_lo) is also reported as a sensitivity column.
- *Static baseline, BER:* BER_ref(μ; trajectory) = mean over the window of the interpolated static BER(c(n), μ) with the 3/N_bits floor applied per grid value. The literal reading (static run at c_lo) is also reported.
- *Definitions otherwise unchanged:* rho, rho_th, S*_MSE, and f keep their meaning.

**Evidence.** In the pilot, with the literal baseline rho at the slowest S (S = 1000, μ = 2⁻⁶, primary 14 dB) is 0.20 although no tracking loss is expected there, while with the trajectory baseline it is −0.01. Comparing S*_MSE under the two readings over all 30 (channel, SNR, mu) combinations: at rho_th = 0.5 they are identical in 27, differ by one grid step in 2, and are undefined under the literal reading in 1 (candidate A, mu = 2^-6, 14 dB); at rho_th = 0.75 identical in 27 and one step in 3; at rho_th = 0.25 identical in 21, one step in 7, undefined under the literal reading in 2. On the primary channel (10 combinations) the counts are 9 identical and 1 one-step at rho_th = 0.5, 10 identical at 0.75, and 6 identical and 4 one-step at 0.25. The choice therefore moves the MSE boundary by at most one grid step where it is defined, but it changes the BER boundary completely (literal baseline: S*_BER undefined for most primary-channel cases). **Recommendation: adopt the trajectory baseline as primary and report the literal one as a sensitivity.**

### P-06 — Equalizer length and delay  [PROVISIONAL]
L = 16 (D-07). Delta is chosen **once** (it is a hardware constant), not per coefficient value or SNR.
**P1 result (V5, L1):** the MSE-versus-Delta curve is flat from Delta = 0 to about 12 on the control channel and nearly flat from 0 to about 8 on the primary channel, then rises steeply near Delta = L + M - 2. The smallest Delta whose oracle MSE is within 2 % of the best Delta at every coefficient value of the primary trajectory and at both pilot SNRs is **Delta = 2** (worst case 1.34 % above the best). Adopted provisionally; frozen at FREEZE-1. The oracle's own argmin is 3 to 6 depending on case, which is why a flat minimum needs a stated rule rather than a bare argmin.

### P-07 — Training sequence  [PROVISIONAL]
PRBS x^15 + x^14 + 1, seed 1, period 32767, N_T = 30000 (less than one period). V6 verified 16384 ones per period and off-peak autocorrelation of exactly -1/32767.
Convergence check (L1, one pilot seed, a = 0.3125, 14 dB, supervised): the 500-symbol moving-average MSE is within 10 % of its final value after 965, 1392, 2378 and 4009 symbols for mu = 2^-7, 2^-8, 2^-9, 2^-10. N_T = 30000 is therefore about 7 times longer than needed for the slowest mu tested. To be rechecked at the harsh end of the primary channel, where the slow mode is slower.

### P-08 — Audio payload  [APPROVED]
Clearly labelled synthetic placeholder until a recorded 5–10 s mono WAV is supplied. The Boolean Board manual confirms a 50 Hz–5 kHz bandpass for its **audio output** circuitry; this must not be presented as a microphone-input specification.

---

## Findings so far (L1, pilot seeds; measured, not final results)

### F-1 — Textbook misadjustment formula underestimates on the ISI channel  [FINDING; investigated 20 Oct; CLASSIFIED: incorrect use of a theoretical approximation; provisionally accepted by the project owner 20 Oct, "fully verified" only after review of `MISADJUSTMENT_DERIVATION.md`]
Full derivation, assumptions, code checks and numerical comparison: `MISADJUSTMENT_DERIVATION.md` (V4b and its record are preserved; V4d is a separate test; `lms_lib.py` SHA-256 recorded in `code/results/original_V4b_preserved/`).
**Original observation (preserved unchanged; raw record in `code/results/original_V4b_preserved/` with SHA-256).** Static control channel a = 0.6016, 14 dB, Delta = 2, four seeds of 1e6 symbols:

| mu | measured excess MSE | formula mu·tr(R)/2 / (1 − mu·tr(R)/2) | ratio |
|---|---|---|---|
| 2^-8 | 6.75 % ± 0.13 | 4.55 % | 1.48 |
| 2^-9 | 3.29 % ± 0.12 | 2.22 % | 1.48 |
| 2^-10 | 1.62 % ± 0.12 | 1.10 % | 1.48 |

V4b (formula within 20 %) **fails as pre-registered and stays failed**. The LMS loop, the 20 % tolerance and the measured numbers were not changed. The investigation (`code/investigate_misadjustment.py`, log `results/misadjustment_console_log.txt`, data `results/misadjustment_investigation.json`, figure `fig_M1_misadjustment_investigation.png`) established:

1. **Formula and assumptions.** Excess/J_min = q/(1−q), q = mu·tr(R)/2, tr(R) = L(Σh²+σ²). It rests on (A1) small mu, (A2) input independent of the weight error, (A3) the optimal-filter error e_o(n) is white and independent of the input. A3 is the assumption that fails here. The eigenvalue form Σ mu·λ/(2−mu·λ) differs from the trace form by only 1–2 % at mu = 2^-9…2^-10 (R: eigenvalues 0.28…2.88, cond 10.4), so the eigenvalue spread of R is NOT the explanation.
2. **Implementation audit: no bug.** A plain-python LMS matches the project loop to 9e-16; a separately written row-based LMS matches it exactly (0.0); d[n] = x[n−Delta] exactly; Wiener error by rows equals Wiener error by convolution; the fixed Wiener filter measures 0.02734 ± 0.00004 against J_min = 0.02736 (ratio 0.9994); the steady-state window is flat (block MSEs show no trend) and starts 25 times later than the convergence time.
3. **Measurement: no issue.** 16 independent seeds × 1e6 symbols (window 9e5). Paired estimator (LMS MSE minus fixed-Wiener MSE on the same data) and the original unpaired estimator agree within 2 %; 95 % CI of the paired ratio is ±0.003 to ±0.004. Table below.
4. **Mechanism.** The residual error e_o of the best fixed filter is strongly correlated in time on an ISI channel (lag-1 autocorrelation −0.534, lag 2 +0.216; white would be 0 ± 0.0005). The gradient-noise covariance at lag 0, C(0) = E[e_o² uᵀu] = 0.6058, equals J_min·tr(R) = 0.6092 within 0.6 % (so the "size" of the gradient noise is as the textbook says), but C(1) = −0.1535 and C(2) = +0.0094. To first order in mu, J_ex = (mu/2)·(C(0) − 2Σ_{j≥1}C(j)) instead of (mu/2)·C(0); here Σ_{j≥1}C = −0.144, giving (0.606 + 0.288)/0.609 = 1.468 times the textbook value.
5. **Independent checks of the mechanism.** (i) Exact fourth-moment algebra (no simulation, no fitted parameter) predicts 1.468 and the measurement is 1.468–1.480 (ratio meas/exact 1.055, 1.026, 1.011 at mu = 2^-8, 2^-9, 2^-10; deviation halves with mu, consistent with a second-order-in-mu term that the first-order model omits). (ii) Time-shuffled rows (same LMS update, correlation destroyed) give 0.99–1.00 of the textbook value (±0.007). (iii) A first-order linearised LMS run on the real correlated data gives 1.40–1.46 (→ 1.47 as mu → 0). (iv) Gaussian data: ratio 1.48–1.50, and the exact model with Gaussian moments gives 1.06–1.015 agreement, so binary data is not the cause. (v) Flat channel: ratio 0.996 ± 0.005 and e_o is white (autocorrelation 0.0000).
6. **ISI sweep (mu = 2^-9, s = 0 flat to 1.5).** meas/textbook rises monotonically 0.996 (s = 0) → 1.023 (0.2) → 1.151 (0.5) → 1.473 (1.0) → 1.750 (1.5, a = 0.90, cond R 43); lag-1 residual autocorrelation goes 0 → −0.76 in step; the exact model tracks it, meas/exact 1.015…1.041 (rising slowly, the second-order term grows with cond R). The textbook formula is within 20 % only for s ≲ 0.6 (a ≲ 0.36).
7. **Classification: incorrect use of a theoretical approximation** (white-residual-error assumption A3). Not an implementation bug, not a measurement issue, not unresolved at the 20 % level. Residual 1–6 % (mu = 2^-10 … 2^-8; 12 % at 2^-7) is the second-order term, not separately modelled.
8. **Consequences.** (a) eps_static(mu) is measured, so no metric definition changes (unchanged from before). (b) For analysis of mu_opt or of the noise-versus-lag trade-off on the primary channel (a up to 0.906, similar to the s = 1.5 row) the textbook formula must NOT be used quantitatively: it underestimates by up to about 1.75×; the first-order correlated-error model `exact_C` is the reference. (c) Linearity in mu (the thing the exponent analysis relies on) is confirmed (excess ratios 2.0 between successive mu). (d) New test **V4d** (reference model, same 20 % criterion) passes; V4b is kept beside it.
9. **Statement for the report.** "The textbook independence-theory misadjustment assumes a white optimal-filter error. On the ISI channel the error is correlated (lag-1 coefficient −0.53), which raises the excess MSE by a factor 1.47 at first order; a model that includes the correlation reproduces the measurement to within 1–6 %."

Per-mu table (control channel, J_min = 0.02736, 16 seeds × 1e6, window 9e5; "paired" = LMS MSE − fixed-Wiener MSE on the same data; CI 95 %, t-interval over seeds):

| mu | measured MSE | measured excess (abs) | textbook excess (abs) | first-order exact (abs) | meas/textbook (paired ± CI) | meas/first-order exact |
|---|---|---|---|---|---|---|
| 2^-7 (outside V4 set) | 0.03125 ± 0.00003 | 3.902e-3 | 2.607e-3 | 3.493e-3 | 1.497 ± 0.003 | 1.117 ± 0.002 |
| 2^-8 | 0.02919 ± 0.00003 | 1.842e-3 | 1.244e-3 | 1.746e-3 | 1.480 ± 0.003 | 1.055 ± 0.002 |
| 2^-9 | 0.02825 ± 0.00003 | 8.956e-4 | 6.082e-4 | 8.732e-4 | 1.473 ± 0.003 | 1.026 ± 0.002 |
| 2^-10 | 0.02779 ± 0.00003 | 4.416e-4 | 3.007e-4 | 4.366e-4 | 1.468 ± 0.004 | 1.011 ± 0.003 |

Original unpaired ratios (excess relative to theoretical J_min): 1.494, 1.474, 1.460, 1.443 (slightly lower than paired because the realised fixed-filter MSE differs from J_min by finite-sample noise at the 0.1 % level).

### F-2 — Frozen filter versus oracle preview  [FINDING, single pilot seed, not a tracking result]
Primary channel, 14 dB, mu = 2^-8, supervised, one seed: the excess MSE of R2 over the oracle is about 400 % (R2 MSE about 5 times the oracle) at S = 1000, 200 and 50, averaged over complete triangle periods. The excess of R3 is 7 %, 11 % and 32 % at those rates (static misadjustment at this mu is about 7 % on the control channel). The analytic prediction for the frozen filter's excess was 3.9 (Delta = 4); the measurement used Delta = 2 and gave 4.0. Final numbers need many seeds and the frozen thresholds.

### F-3 — Development note  [RECORDED FOR HONESTY / VIVA]
The first PRBS generator mapped taps to the wrong register bits and produced an all-zero sequence after one bit. It was caught by a smoke test (R2 MSE 0.97 against R3 0.02). After the fix the V6 tests confirm period 32767, 16384 ones and correct autocorrelation. This is why the period and balance tests exist.

## Register: PPR-22 statement → refinement (to be reproduced in the midterm report)

| ID | Original statement in PPR-22 | Refinement | Why | Research objective changes? |
|---|---|---|---|---|
| R-1 | Sec. 5.2/10: mu_opt should scale as the square root of the variation rate | Square root kept as random-walk reference; 2/3 ramp exponent as conditional alternative; measured exponent reported | The trajectories are deterministic ramps, not random walks | No: the optimum-step-size study is kept |
| R-2 | Sec. 3.1/5.7: boundary S\* defined by BER (R3 within a factor of static BER) and by R3 ceasing to outperform controls | BER criterion kept (S\*_BER, S_cross); oracle-normalized MSE added (S\*_MSE); both reported | Bounded trajectories saturate; BER may not move when the eye is open | No: the boundary is still located, now from two angles |
| R-3 | Sec. 4.2: h = [1, a, 0.1], a in [0.2, 0.6], Delta_a unspecified | Delta_a = 2^-7; counters 26–77 for the control | Needed for a reproducible trajectory in RTL | No |
| R-4 | Sec. 4.1: Nrec relative to pre-transition steady state | Relative to post-transition steady state, sustained over a window | h_B has a different attainable MSE | No |
| R-5 | Sec. 4.2 (only one channel) | Mild channel kept as control; harsher primary channel added | Mild channel never closes the eye | No: strengthens the BER evidence |
| R-6 | Sec. 5.4: PRBS gives R ≈ sigma^2 I | R ≈ H H^T + sigma^2 I; PRBS remains best simple excitation | Received signal is filtered by the channel | No |
| R-7 | Sec. 6.2: mismatch grows without bound; fixed example numbers | Bounded; condition is a deadband that depends on rounding and e statistics | Bounded trajectory; example was illustrative | No |
| R-8 | Sec. 6.2/6.4: single word length B | B_mul and B_acc | Underflow depends on the accumulator, DSP cost on the multiplier | No: sharpens objective 5 |
| R-9 | Sec. 6.5/Table 3: 51 DSP48E1 fully parallel | **No change.** A time-multiplexed MAC was proposed and approved earlier, then withdrawn by the project owner before any RTL work; the PPR-22 parallel plan stands (estimate only until L4) | Owner preference; no simulation depends on it | No |
| R-10 | Sec. 5.1 (SNR not defined) | Eb/N0 relative to transmitted symbol energy | Needed for the BER-vs-theory baseline | No |
| R-11 | Sec. 15 AI disclosure | Revised wording (spec Sec. 10) | Course policy: identify AI-generated parts | No |


### F-4 — Training length at the harsh end of the range  [FINDING, L1 pilot; closes the P-07 recheck]
Static-training convergence (500-symbol moving average of the 100-seed mean within 10 % of the static steady level): channel a = 0.3125 (c = 40): 995, 1581, 2628, 4788 symbols for mu = 2^-7 … 2^-10; channel a = 0.9063 (c = 116): 2619, 4797, 10468, 20084 symbols. N_T = 30000 therefore leaves a 6× margin at the primary start value (c = 40), but only 1.5× at c = 116 for mu = 2^-10. MSE convergence also does not guarantee convergence of every coefficient: R2 frozen at N_T after training on c = 116 and then used on c = 40 measured 0.6124 (mu = 2^-10) and 0.6869 (mu = 2^-9) against the analytic 0.7006 (−12.6 % and −2 %), because the weakly excited mode (lambda_min of R is about 0.08 at c = 116) has not converged: the mean-weight model started from zero weights and run for N_T = 30000 symbols predicts 0.6112 (mu = 2^-10) and 0.6917 (mu = 2^-9) for the frozen filter on c = 40 (measured 0.6124 and 0.6869), and 0.7005/0.7006 at mu = 2^-8/2^-7. Consequence: the planned design (static training at c_lo = 40, variation starting upward) is unaffected; any design that trains at the harsh end needs N_T of several times the 10 % time (about 60000 at mu = 2^-10).

### F-5 — P2 abrupt-transition results  [L1 pilot, 100 pilot seeds, 14 dB, supervised LMS; code `p2_abrupt.py`, log `results/p2_console_log.txt`, data `results/p2_results.json`]
- *Frozen filter (R2) after the transition.* Measured seed-mean MSE after the transition against the analytic frozen-filter MSE: large_up 0.3972 vs 0.3965 (mu = 2^-8; excess 674 % over the oracle), mid_up 0.1126 vs 0.1119 (309 %), down 0.6920 vs 0.7006 (3185 %; 0.6124 at mu = 2^-10 because of F-4).
- *Static levels (D-09 reference).* eps_static = (J_ss − J_min)/J_min on the static channel: c = 40: 8.95, 4.33, 2.14, 1.08 %; c = 77: 14.35, 6.81, 3.35, 1.68 %; c = 116: 24.2, 11.1, 5.34, 2.65 % for mu = 2^-7 … 2^-10 (first-order exact model of F-1: 8.2, 4.1, 2.1, 1.0 / 12.8, 6.4, 3.2, 1.6 / 20.2, 10.1, 5.0, 2.5 %).
- *Reacquisition (kappa = 0.25, W = 64), N_rec in symbols, measured [95 % bootstrap] | model with measured static level | model + noise band (95 %)* — all 12 measured values lie inside the noise-corrected model band:

| step | mu | measured [CI] | model, noise-free | model + noise |
|---|---|---|---|---|
| large_up | 2^-7 | 1109 [1089, 1373] | 1002 | 1152 (971–1420) |
| large_up | 2^-8 | 2674 [2410, 3532] | 2113 | 2527 (2213–2978) |
| large_up | 2^-9 | 5444 [5398, 7413] | 4329 | 5437 (4804–6383) |
| large_up | 2^-10 | 10961 [10975, 19057] | 8758 | 11413 (10273–13157) |
| mid_up | 2^-7 | 357 [329, 400] | 342 | 344 (313–373) |
| mid_up | 2^-8 | 738 [613, 790] | 660 | 682 (612–761) |
| mid_up | 2^-9 | 1336 [1316, 1595] | 1295 | 1378 (1253–1543) |
| mid_up | 2^-10 | 2796 [2690, 3333] | 2566 | 2788 (2560–3034) |
| down | 2^-7 | 512 [493, 543] | 511 | 511 (495–529) |
| down | 2^-8 | 981 [971, 1068] | 982 | 988 (956–1026) |
| down | 2^-9 | 1934 [1912, 2061] | 1925 | 1943 (1884–2030) |
| down | 2^-10 | 3868 [3797, 3986] | 3811 | 3885 (3766–4026) |

  Log–log slope of N_rec versus mu: measured −1.09 (large_up), −0.98 (mid_up), −0.97 (down); mean-weight model −1.09, −1.02, −1.00, i.e. N_rec is proportional to 1/mu. The ratio of the measured excess-MSE area after the transition to the model's area is 1.058, 1.022, 1.012, 1.007 (large_up), 0.940–0.996 (mid_up), 0.928–0.977 (down).
- *The N_rec statistic is biased upward by noise.* "Last time above the threshold" is a one-sided statistic; the measured value exceeds the noise-free model by up to 25 % on the harsh channel (large_up) because the 64-symbol moving average of e^2 there has 3.61 times the variance of an iid Gaussian average (1.18 at c = 40, 1.72 at c = 77; weight-error jitter correlates e^2 over the window). A Monte Carlo of the model curve with these measured noise factors reproduces the measured values (table, last column; `p2_nrec_noise_check.py`). The bootstrap interval is a percentile interval and can sit above the point estimate for this reason. No definition is changed (D-09 stands); the final report states the interval and the noise-free model value.
- *BER around the transition (mu = 2^-8, 100 seeds; blocks 500 symbols; `fig_P2_ber_vs_time.png`).* large_up: R1 0.151 after the step, R2 1.8e-2, R3 1.8e-3 in the first 2000 symbols and 2.9e-5 in the last 20000. mid_up: R1 4.3e-3, R2 7.5e-6, R3 0 (no error in 2e6 bits) although R2's MSE is 309 % above the oracle: BER and MSE tell different stories here, which is why both are reported. down: R1 0.150 before the step, R2 0.146 after, R3 7.5e-3 in the first 2000 symbols and 0 afterwards.
- *Coefficient trajectories (`fig_P2_coefficients.png`).* Mean R3 coefficients follow the mean-weight model E[w(n)] = w_B + (I − mu R_B)^k (w_A − w_B) throughout (dotted curves on top of the measurement).

### F-6 — P3 continuous-variation pilot  [L1 pilot, 20 pilot seeds (1000–1019), supervised LMS, 3 channels × {14, 16} dB × 10 S × 5 mu; code `p3_run.py`, `p3_analyse.py`, log `results/p3_analysis_log.txt`, data `results/p3_results.json`, `p3_raw.npz`]
S grid {1000, 500, 200, 100, 50, 20, 10, 5, 2, 1} symbols per coefficient step, plus the literal static S0 run; mu in {2^-6 … 2^-10}; evaluation window 152000 symbols (one full triangle at S = 1000 on the primary channel; fewer than two periods on the other two at S = 1000, the same window being used for the oracle).
- *Selection rule (frozen order: control, candidate [0.50, 0.90], primary).* C1 (eps_plateau ≥ 1): control 0.60/0.98 and candidate 0.51/0.85 **fail** at 14/16 dB; primary 1.12/1.83 **passes**. C2: all pass (primary cond(R) 50.9/56.0, min|H| 0.194). C3a: all pass. C3b (R2 expected ≥ 100 errors in 1e7 bits at some S): control **fails**; candidate and primary pass. C4 (bracketing at rho_th = 0.5, monotonic, ≥ 2 pass and ≥ 2 fail points) passes for every channel and every mu. **Only the primary channel satisfies C1–C4, at both SNRs.** The final SNR choice is left to the owner (14 dB: C1 margin 12 %, more errors at slow S; 16 dB: C1 margin 83 %, wider MSE range).
- *S*\*_MSE, primary 14 dB, rho_th = 0.5 (trajectory baseline, P-12):* mu = 2^-6 … 2^-10 gives 20, 20, 50, 50, 100; rho_th = 0.25 / 0.75 give 20, 50, 50, 100, 200 / 10, 10, 20, 50, 50. The MSE passing sets are monotonic in all 180 cases (3 channels × 2 SNR × 5 mu × 3 rho_th × 2 baselines). Primary 16 dB (0.5): 10 … 100 in the same order of mu: 10, 20, 50, 50, 100. Slower S is needed as mu falls, as expected.
- *S*\*_BER (f = 2, trajectory baseline):* primary 14 dB: 20, 50, 200, 200, 1000 for mu = 2^-6 … 2^-10; primary 16 dB: 20, 50, 50, 100, 100. S*_BER is equal to or at slower S than S*_MSE (a stricter criterion at small mu), e.g. mu = 2^-8 at 14 dB: R3 BER 1e-6 at S = 1000, 3e-6 at S = 100 and 2e-5 at S = 20 while rho is 0.00, 0.10 and 0.57. The BER passing sets (trajectory baseline) are monotonic in 72 of 90 (channel, SNR, mu, f) cases (the 18 exceptions: control 14 dB 4, candidate A 14 dB 6, candidate A 16 dB 7, primary 16 dB 1; none on primary 14 dB), so S*_BER is stated only where monotonic and the passing set is reported otherwise. With the literal baseline (static run at c_lo, zero errors) S*_BER is mostly undefined (P-12).
- *S_cross:* R3 has a significantly lower BER than both R1 and R2 at every grid point of the primary channel, including S = 1: no S_cross is observed within the grid (BER of R3 at S = 1 is 8e-5, 2e-4 and 7e-4 for mu = 2^-8, 2^-7, 2^-6, against about 2e-3 for R2 and 3e-2 for R1, 14 dB).
- *Saturation.* For S ≤ 5 rho stays between 1.00 and 1.14 (mu ≤ 2^-8, primary 14 dB): R3 behaves like a fixed averaged filter; the analytic plateau is quasi-static, so a value a few percent above 1 is expected (the exact oracle is lower by up to about 2 % at S = 1). mu = 2^-6 gives rho up to 1.84 (worse than a fixed filter: misadjustment plus lag). Candidate A at mu = 2^-6 gives rho up to 7.8 because its plateau is small (0.51), which is what C1 guards against.
- *mu_opt preview (not a result; five-point mu grid, parabolic refinement, points at the grid boundary or in the saturated region excluded, 1 s.e. statistical only):* slope of log2 mu_opt against log2(1/S): primary 14 dB 0.49 ± 0.02 (S ≥ 20; 0.33 ± 0.07 if the saturated S = 5 point is wrongly included), primary 16 dB 0.53 ± 0.01, control 0.56 ± 0.02 and 0.59 ± 0.01. This is between the reference exponents 1/2 and 2/3 and does not yet discriminate; the final study needs a finer mu grid and 100 seeds.
- *Baseline ambiguity (see P-12).* With the literal static baseline rho at S = 1000, mu = 2^-6 (primary, 14 dB) is 0.20; with the trajectory baseline it is −0.01.

---
## 20 Oct 2026 — owner approvals and FREEZE-1 preparation
- **P-10 APPROVED with clarification:** Wilson 95 % intervals; 3/N_bits is a zero-error upper-bound convention (BER_ref,UB), never an observed BER; pass 'P' if upper ≤ f·BER_ref, fail 'F' if lower > f·BER_ref, otherwise '?' (inconclusive, not passing). BER_ref is *resolved* if N_bits·BER_ref,obs ≥ 100; otherwise reference-limited (threshold uses UB; a pass is 'p' = conditional, a fail stays rigorous). S*_BER only if monotonicity is demonstrated (all points after the first non-pass fail). "No S_cross observed within the grid" if R3 outperforms R1 and R2 everywhere. *(Implemented in `sweep_analyse.py`.)*
- **P-11 APPROVED with correction:** V2 uses Bonferroni familywise exact intervals (per-point level 1−0.05/12), pooled χ² (α 0.01), sign test (α 0.01), ≥100 errors per point; a single failing run is INCONCLUSIVE and needs replicates. Original V2 results preserved (`p1_validation.py` unchanged). History: original V2 pass; revised V2 pass on the same data; sign test flagged one replicate (11/12 above theory, p=0.006); 20-replicate arbitration gave a pooled flag (p=0.003); RNG tail test showed the generator unbiased; 100 further replicates did not confirm (p=0.456). No implementation bug declared. (`v2_*.json`/`_log.txt`.)
- **P-12 APPROVED with conditions:** primary baseline = trajectory-averaged *measured* static LMS performance (11 c values, linear interpolation, weights = occupancy of c(n) in the evaluation window); oracle enters only via J_min and the normalising J_or. Literal PPR-22 baseline (static run at c_lo) retained as separate sensitivity column. Measured static LMS is never replaced by oracle performance.
- **Operating point:** 16 dB primary, 14 dB secondary. **Thresholds:** ρ_th = 0.5, f = 2, bands 0.25/0.75 and 1.5/5, documented as refinements relative to PPR-22.
- **Caveat on the earlier P3 pilot:** its BER baseline applied a floor per grid value (averaging UB values); superseded by the obs/UB convention above. Pilot S*_BER values from `p3_analyse.py` are therefore indicative only.
- **BER resolution finding (16 dB):** reference-limited for μ ≤ 2^−7 with 100 seeds × 152000 symbols; see FREEZE_1_PROPOSED.md §4 (options A/B/C, awaiting decision). Grid pilot: `grid_pilot_*`, `grid_pilot_analysis_*` (L1 pilot).
- **P-13 PROPOSED (not frozen):** μ half-octave grid 2^−5…2^−11.5 (powers of two 2^−5…2^−11 for FPGA), S grid of 18 values 5000…1, window rule N_eval(S). See FREEZE_1_PROPOSED.md.

---
## 20 Oct 2026 (later) — FREEZE-1 validation checks (L1 pilot)
- **N_T = 30000 verified** for all 14 μ against the Wiener reference (`check_NT*`); no change.
- **Window rule verified** (exact lengths and weights in FREEZE_1_PROPOSED.md §1; S = 224 is −10.4 %, S = 2000/5000 use 2/5 periods' worth of length because one period is the minimum). Statistical half-width of ρ ≤ 0.005 at 100 seeds.
- **Budget correction:** earlier "≈2 h per SNR" was wrong; projected ≈ 8–10 min per SNR (pilot-rate projection).
- **12 dB static BER measurable** (≥ 297 expected reference errors, all μ, 100 seeds); 14 dB only for μ ≥ 2⁻⁶·⁵; 16 dB only for μ ≥ 2⁻⁵·⁵.
- **Proposed A-1:** log-linear interpolation of the static BER when all nodes are non-zero (linear over-estimates by 4–8 %; independent S = 5000 check at 12 dB agrees to 0.96–1.02 with log-linear). **Proposed A-2:** 12 dB standard + 14 dB 1500-seed BER study. Status of A-1 … A-3: PROPOSED, awaiting confirmation. Original P-12 text (linear interpolation) is preserved above; A-1 would amend only the BER baseline.

---
## 20 Oct 2026 (later) — D-12 BER reporting limit and noise labelling  [APPROVED by the project owner]
PPR-22 Sec. 4.3's limit (BER quoted only down to about 1e-4 for the LFSR sum-of-uniforms noise generator) is a hardware-generator limit and is **not** a contradiction of the L1 work. L1 (ideal Gaussian noise) BER is reported over its full range with a dashed line at 1e-4 on every BER figure, labelled as the validity limit of the planned hardware noise generator, and the report states once that simulation extends beyond it while hardware (L3–L5) BER is quoted only down to about 1e-4. Comparison document: C-10 reclassified as a labelling note. Also recorded: 12 dB static BER for small mu is about 2e-5, so hardware BER at small mu will need a lower SNR (to be measured at that stage).

---
## 20 Oct 2026 (later) — FREEZE-1 decisions by the project owner (items 1–4); item 5 on hold
| Item | Decision | Condition recorded |
|---|---|---|
| 1. A-1 BER-baseline interpolation | **APPROVED CONDITIONALLY** | Log-linear interpolation is used (primary) where all 11 static nodes have ≥ 1 error because BER is positive and spans orders of magnitude; **linear interpolation is retained and reported as a sensitivity comparison**; the report must **not claim log interpolation is the true BER between nodes** — it is a modelling assumption. Supporting evidence only (not proof): at 12 dB, S = 5000, the measured R3 BER agrees with log-linear within 0.96–1.02 and with linear within 0.90–0.97 (`ber_baseline_check_log.txt`). |
| 2. A-2 BER study design (12 dB 100 seeds; 14 dB 1500 seeds for μ ≤ 2⁻⁷; 16 dB reference-limited) | **APPROVED** | Owner asked to confirm that errors are independent enough for the stated intervals. **Check done (`check_error_independence.py`, 12 and 14 dB, 40 seeds 5300–5339): they are NOT independent.** P(error at n+1 \| error at n) is 0.05–0.29 against an overall BER of 10⁻⁵–10⁻³; errors come in short bursts. Burst size (errors closer than 20 symbols merged): 1.07–1.22 errors per burst for μ ≤ 2⁻⁷ and 1.7–1.9 for μ = 2⁻⁵. Per-seed dispersion index 0.6–2.6 (noisy, few counts per seed). Plain Wilson on pooled error counts therefore understates the variance by roughly this design effect (interval too narrow by about 3–10 % for μ ≤ 2⁻⁷, up to about 37 % for μ = 2⁻⁵). **Amendment A-4 PROPOSED (see below).** |
| 3. A-3 run-time correction | **APPROVED** | A computational estimate, not a methodological deviation. |
| 4. Whole-period window | **APPROVED** | Accepted provided every grid point uses its own actual N_bits and N_eval (implemented: `sweep_analyse.py` uses N_bits = seeds × actual N_eval) and the intervals use that count. |
| 5. Classification of contradictions / extensions / gaps (`PPR22_COMPARISON.md`) | **ON HOLD** | Register rows R-12 … R-18 not yet added. |

### A-4 — Burst-adjusted BER intervals  [PROPOSED, needs approval; consequence of the independence check]
Pass/fail uses the Wilson interval on the number of independent **error bursts** C (consecutive errors < 20 symbols apart form one burst; 20 > L and covers the equalizer memory), scaled back to bit errors by the pooled mean burst size m̄ = k/C: BER interval = m̄ × Wilson95(C, N_bits). Thresholds (f × BER_ref), the resolved criterion (N_bits × BER_ref,obs ≥ 100) and the pass/fail/inconclusive logic of P-10 are unchanged; the reference BER_ref gets the same treatment. The plain-Wilson intervals are retained as a sensitivity column. A seed-level bootstrap of the error counts (final run: 100 seeds, or 1500 at 14 dB) is added as an independent cross-check that makes no assumption about burst structure. Needs one change to the data collection (not to the LMS): the sweep must store the burst count per record next to the error count. The earlier pilots stored only error counts, so their BER statuses are plain-Wilson; the grid pilot can be re-run (about 10 min per SNR) to show the effect of A-4 before the final sweep.

---
## 20 Oct 2026 (evening) — owner decisions on the audit (E-1 … E-7) and implementation status
| # | Decision | Implemented as |
|---|---|---|
| E-1 | **MODIFIED and approved:** paired seed-level bootstrap is the PRIMARY BER comparison where the reference has sufficient observed errors; within-seed temporal dependence and trajectory/static pairing preserved; burst-adjusted Wilson and plain Wilson are sensitivity checks only; the bootstrap must be validated; reference-limited/inconclusive classes kept. Supersedes the proposed A-4 as primary method. | `sweep_analyse.py` v2: `paired_ratio` (whole seeds resampled, same resample for trajectory and static runs; B = 2000); "sufficient" = expected reference errors ≥ 100 in the trajectory window AND in the static runs; otherwise reference-limited (Wilson vs f·BER_ref,UB). Validation: `validate_bootstrap_run.py` / `validate_bootstrap_analyse.py` (40 independent replicate experiments, seeds 300000–301999). |
| E-2 | **APPROVED:** store burst counts, per-seed error counts, actual bit counts and pairing information. | `sweep.run_point_full`: per-seed E1–E3, bursts B1_20, B2_20, B3_10/20/40, n_bits; metadata seeds, static_seeds, paired flag. Regression check: identical numbers to the earlier engine (`run_point` unchanged interface). |
| E-3 | **APPROVED:** S_cross bug fix; distinguish confirmed loss of advantage from inconclusive evidence. | Paired bootstrap of BER_R3 − min(BER_R1, BER_R2): A / L (confirmed loss) / ? per S; z-test kept as a sensitivity string. |
| E-4 | **APPROVED:** mild control channel (counters 26–77) in the final sweep. | `freeze_grids.CHANNELS_FINAL`, control static nodes 26, 34, 42, 50, 58, 66, 74, 77. |
| E-5 | **APPROVED:** 14 dB BER-study seeds 100000–101499. | `freeze_grids.BER14_SEEDS`. |
| E-6 | **MODIFIED:** P2 must start from adequately converged filters in all three scenarios; check a common N_T = 60000 and validate before freezing; the continuous sweep keeps N_T = 30000. | `check_NT_p2.py` (log `results/check_NT_p2_log.txt`): with N_T = 30000 the c = 116 training ("down" step) FAILS at μ = 2⁻¹⁰ (16 dB: frozen-filter MSE +1.45× the LMS excess above the long-training reference; 14 dB: +0.61×); with **N_T = 60000 all 16 cases PASS** (2 training channels × 2 SNR × 4 μ; model residual ≤ 2.2 % of the LMS excess, measured difference within its 95 % interval). Proposed for FREEZE-1: common N_T = 60000 for P2. |
| E-7 | **MODIFIED:** replace the nine-item list by four precisely labelled issues: AI-disclosure conflict, incorrect R approximation, bounded-channel mismatch overstatement, midterm schedule deviation; not all described as experimental contradictions. | `PPR22_COMPARISON.md` rewritten; register rows below. |
| A-1 | Implement log-linear BER interpolation (approved earlier, missing in code). | `sweep_analyse.py` v2: log-linear where every node has ≥ 1 error, linear otherwise; linear always reported as a sensitivity column. |
| — | Document the exponent-fit sensitivity. | `sweep_analyse.exponent_variants` (7 predeclared variants). Grid pilot (L1 pilot): 16 dB baseline 0.519, systematic spread 0.486–0.544, statistical 95 % 0.519–0.520; 14 dB 0.525, spread 0.493–0.550. Report the systematic band, not only the statistical interval. |
Owner note: the AI-disclosure item is a low-priority wording fix (the course only requires disclosure of AI use); the priority is meeting the objectives by 25 Oct.

### Register rows added (E-7)
| ID | Original statement in PPR-22 | Refinement | Why | Research objective changes? |
|---|---|---|---|---|
| R-12 | Sec. 15: no simulation output is AI-generated | Revised disclosure stating where AI was used (D-06) | The original sentence does not describe this project; the course requires disclosure only | No |
| R-13 | Sec. 5.2: misadjustment "roughly μ tr(R)/2" | Finding F-1: 1.47× on this channel; correlated-error model | The white-error assumption fails on an ISI channel | No |
| R-14 | Sec. 9: midterm = P1–P6 | P5 and P6 planned before 25 Oct (P6a scope); any remaining P6 items stated as deferred | Time | No |
| R-15 | Sec. 4.3: BER quoted only down to ≈ 10⁻⁴ | Applies to the hardware LFSR noise; L1 uses ideal Gaussian noise (validated to 2.7·10⁻⁷), labelled, with a dashed 10⁻⁴ line (D-12) | Different generator at L1 | No |
| R-16 | Table 2 presets S1–S4 | 18-value S grid, 14 μ values (7 powers of two) | PPR-22 asked for presets fixed after simulation to bracket the boundary | No |
| R-17 | Sec. 10: one fixed operating SNR | 16 dB primary, 14 dB secondary; BER study at 12/14 dB | BER reference unmeasurable at 16 dB for small μ | No |
| R-18 | Sec. 5.7: "static-channel value" | Trajectory-averaged measured static baseline; literal c_lo kept | Misadjustment depends on channel state | No |
| R-19 | (BER statistics not specified) | Paired seed-level bootstrap primary; Wilson variants as sensitivities | Error bursts; reference uncertainty | No |
| R-20 | (P2 training length not specified) | N_T = 60000 for P2, 30000 for the continuous sweep | "Down" step trains on the harsh channel | No |

### E-1 validation result (20 Oct, evening; L1 validation data, seeds 300000–301999)
40 independent replicate experiments × 50 seeds, 12 dB, μ ∈ {2⁻⁵, 2⁻⁸} × S ∈ {20, 1000}. Paired seed-bootstrap 95 % intervals cover the pooled truth in 148/160 cases (92.5 %; consistent with 95 %, slightly low); bootstrap SD / actual replicate spread 0.88–1.09. Plain Wilson for R3 alone: SD ratio 0.61–0.90, coverage 33–38/40 (too narrow when bursts are large); burst-adjusted Wilson 0.84–1.02. Pairing correlation +0.18 … +0.52. Slow-limit check: true ratio 1.00–1.02 at S = 1000. Log/linear interpolation differ by 4–7 % in the ratio. Log: `results/validate_bootstrap_log.txt`.

---
## 20 Oct 2026, 18:21 IST — FREEZE-1 APPROVED by the project owner; final L1 sweep authorised
- Frozen configuration = `FREEZE_1_CHECKLIST.md` (grids, windows, seeds, control channel, statistics, interpolation); P2 with common **N_T = 60000**; the continuous tracking sweep keeps N_T = 30000. Paired seed-level bootstrap accepted as primary BER evidence.
- **Owner rule added at approval: reference resolution uses OBSERVED error counts.** Implemented in `sweep_analyse.py`: a point is "resolved" only if the observed static errors, weighted exactly as the static nodes enter the reference (Σ v_j K_j), are ≥ 100, AND the expected reference errors in the trajectory window are ≥ 100. Pass/fail/inconclusive classes and all sensitivity checks kept.
- Final runs launched 20 Oct (`final_sweep.py`, `p2_final.py`, chains `run_chain_A.sh` / `run_chain_B.sh`). `p2_abrupt.py` (pilot) is kept unchanged; `p2_final.py` is a copy with N_T = 60000, final seeds 2000–2099 and Eb/N0 as an argument (16 and 14 dB).
- **P6a word lengths (approved):** B_mul ∈ {8, 12, 16}, B_acc ∈ {16, 26, 32}; baseline B_mul = 12, B_acc = 26, subject to a dynamic-range check. Check done: |w| ≤ 1.10 in every LMS run (Wiener |w| ≤ 0.987) → coefficient formats ±2 (s12.10 multiplier, s26.24 accumulator); |r| ≤ 2.73, |y|, |e| ≤ 3.73 → signals s16.12 (±8). All formats, product widths, rounding and saturation are listed in the `fxp_lib.py` header. LMS equations unchanged.
- **P5:** the payload will be the owner's own voice recording (8 kHz, mono, 8-bit). No synthetic audio deliverable. A temporary test tone is used only for debugging (scratch folder, never presented).
- Levels stay separated: L1 results in `results/final*`, L2 in `results/p6a/`; no FPGA (L3–L5) result exists.

---
## 20 Oct 2026 (evening) — final L1 runs completed; corrections logged during analysis
- Runs completed: primary 16/14/12 dB, control 16/14 dB (100 final seeds), 14 dB BER study (1500 seeds, μ ≤ 2⁻⁷), P2 final 16/14 dB (N_T = 60000). Results: `RESULTS_FINAL_L1.md`, `code/results/final/`.
- Analysis additions (no frozen parameter changed): (1) S*_BER labelled resolved/conditional; (2) ρ marked UNDEFINED when ε_static ≥ ε_plateau (μ = 2⁻⁵ at 12 and 14 dB; earlier code would have printed "no failure within the grid"); (3) descriptive transition bracket where S*_BER is not demonstrated (strict rule unchanged); (4) BER figure shows reference upper bounds for reference-limited points.
- P6a: T7 first attempt with 20 seeds rejected (noise-dominated last-crossing time, identical ≈ 47000 for every configuration; file kept as `T7_first_attempt_20seeds_INVALID.txt`), rerun with 100 seeds. L2 coefficient history aligned to record after the update, as L1 (T1 coefficient difference 2.4·10⁻² → 4.6·10⁻⁵; MSE comparison unaffected).
- **F-7 (finding):** R2 after the P2 "down" step is 0.7–2.7 % below the analytic MSE of the ideal trained filter. Measurement equals the analytic MSE of the actual frozen weights (+0.03 %). At μ = 2⁻¹⁰ the mean-weight model predicts the offset (−2.10 % vs −2.3 % measured): the slowest mode (λ_min = 0.07 at c = 116) retains 1 % weight error after 60000 symbols, invisible in the training-channel MSE check used for E-6 but linear on the new channel. At μ = 2⁻⁷ the offset is linked to the shared PRBS training segment (random training: −0.5 %, not significant). Decision requested: keep N_T = 60000 and report, or rerun P2 with N_T = 120000 (recommended).
