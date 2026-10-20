# Wording submitted for final approval (20 Oct 2026)

Status of each item: **PROPOSED**. Nothing below changes a definition until approved. Numbers quoted are L1 pilot results (pilot seeds 1000–1019 unless stated).

---

## P-10 — BER criteria (S*_BER and S_cross)

**Proposed text.**

1. *Evaluation.* For every (μ, S) grid point the pooled R3 bit-error count over all seeds and the whole evaluation window is used. N_bits = (number of seeds) × N_eval. R1, R2 and R3 are counted on identical data.
2. *Static reference.* BER_ref is the static-channel BER of R3 with the same μ, defined in P-12 (the baseline definition is the same one used for the MSE criterion).
3. *Pass/fail of a grid point.* Let T(f) = f × max(BER_ref, 3 / N_bits) (the "rule of three" floor makes the criterion meaningful when the static error count is zero). The point **passes** if the upper end of the 95 % Wilson interval of the pooled R3 BER is ≤ T(f); it **fails** if the lower end is > T(f); otherwise it is **indeterminate** and counts as not passing.
4. *S*\*_BER.* S*_BER is the smallest S in the grid that passes, **only if** the passing set is monotonic (once a point fails, every faster point fails or is indeterminate). If not monotonic, the passing set and the first failing S are reported and S*_BER is stated as undefined. "No point fails within the S grid" and "fails already at the slowest S" are valid outcomes and are reported as such.
5. *Factor f.* f = 2 is the primary value; f ∈ {1.5, 2, 5} is reported as a sensitivity band. f is fixed at FREEZE-1 from pilot data.
6. *S_cross (PPR-22 Sec. 3.1 wording).* S_cross is the smallest S in the grid at which the pooled BER of R3 is lower than that of **both** R1 and R2 by a one-sided two-proportion z-test at the 5 % level. It is reported only if R3 stops outperforming at some grid point; if R3 still outperforms R1 and R2 at the fastest S of the grid, the report states "no S_cross observed within the grid" (it is not set equal to the fastest S).
7. S*_BER and S*_MSE are reported separately; if they differ the report explains the difference. All parameters (f, floor, test levels, grids) are fixed at FREEZE-1.

**Why it is proposed (evidence).** The factor and the zero-error case were never stated in PPR-22. In the pilot (primary channel) the literal static run has zero errors, so the floor is the reference; with the literal reference R3 "fails" the criterion at slow S for several μ even though the BER is of order 10⁻⁶ to 10⁻⁵, because the trajectory visits harder channels than the static reference does (P-12). In the pilot R3 stays better than R1 and R2 at every grid point (S_cross not observed) while the MSE-based boundary exists.

---

## P-11 — Wording of validation test V2

**Proposed text.** *Test V2 measures the BER of the direct detector on a flat channel (no ISI) at 12 Eb/N0 points from 0 to 8.25 dB, with 2 × 10⁶ bits per point and at least 100 observed errors per point. For each point the exact (Clopper–Pearson) 95 % and 99 % two-sided binomial intervals of the measured BER are computed and compared with Q(√(2 Eb/N0)). The 95 % result is reported for every point. V2 passes if the theoretical value lies inside the 99 % interval at all 12 points. A failing run is repeated once with different seeds before any conclusion is drawn; a systematic deviation (same sign at several points) is treated as a failure irrespective of the intervals.*

**Why it is proposed.** If the simulator were perfectly correct, requiring all 12 points inside the 95 % interval would fail 1 − 0.95¹² = 46 % of the time and the 99 % version 1 − 0.99¹² = 11 % of the time, so a single excursion is not evidence of a fault. Observed (pilot): 11/12 inside 95 %, 12/12 inside 99 %, minimum 247 errors per point (the project spec's earlier text said "within the 95 % interval at each point").

---

## P-12 — Definition of the static baseline (new; found in the P3 pilot)

**Problem.** The spec says eps_static(μ) is measured "on the static S0 run with the same μ" and BER_static is the static BER, but does not say **which channel value** the static run uses. This matters because the LMS misadjustment grows with the coefficient a (finding F-1: static excess 4.3 % at a = 0.31 against 11 % at a = 0.91 for μ = 2⁻⁸). A static run at the starting value c_lo understates the baseline of a trajectory that visits larger a, and the difference is wrongly counted as tracking loss.

**Proposed text.**
- *Static baseline, MSE:* eps_static(μ; trajectory) = [ mean over the evaluation window of (J_static(c(n), μ) − J_min(c(n))) ] / J_or,mean, where J_static(c, μ) is the measured steady-state R3 MSE of LMS on a **static** channel with counter value c (7 values of c spanning the trajectory, 20 seeds each, linear interpolation in c) and c(n) is the actual counter trajectory of the grid point. This is the S → ∞ limit of the same trajectory. The literal reading (static run at c_lo) is also reported as a sensitivity column.
- *Static baseline, BER:* BER_ref(μ; trajectory) = mean over the window of the interpolated static BER(c(n), μ) with the 3/N_bits floor applied per grid value. The literal reading (static run at c_lo) is also reported.
- *Definitions otherwise unchanged:* rho, rho_th, S*_MSE, and f keep their meaning.

**Evidence.** In the pilot, with the literal baseline rho at the slowest S (S = 1000, μ = 2⁻⁶, primary 14 dB) is 0.20 although no tracking loss is expected there, while with the trajectory baseline it is −0.01. Comparing S*_MSE under the two readings over all 30 (channel, SNR, mu) combinations: at rho_th = 0.5 they are identical in 27, differ by one grid step in 2, and are undefined under the literal reading in 1 (candidate A, mu = 2^-6, 14 dB); at rho_th = 0.75 identical in 27 and one step in 3; at rho_th = 0.25 identical in 21, one step in 7, undefined under the literal reading in 2. On the primary channel (10 combinations) the counts are 9 identical and 1 one-step at rho_th = 0.5, 10 identical at 0.75, and 6 identical and 4 one-step at 0.25. The choice therefore moves the MSE boundary by at most one grid step where it is defined, but it changes the BER boundary completely (literal baseline: S*_BER undefined for most primary-channel cases). **Recommendation: adopt the trajectory baseline as primary and report the literal one as a sensitivity.**
