# Stages P2 and P3 — abrupt transition and continuous-variation pilot (level L1)

All numbers are **L1 pilot results** (floating-point simulation, pilot seeds 1000–1099 for P2, 1000–1019 for P3, supervised LMS, Eb/N0 14 dB unless stated). They choose parameters; they are not final results. Run: `python3 p2_abrupt.py`, `python3 p2_nrec_noise_check.py`, `python3 p3_run.py` then `python3 p3_analyse.py` inside `code/` (about 1.5, 1, 2.5 and 0.5 minutes).

## 1. The idea in one paragraph
P1 showed that LMS finds the best filter when the channel stands still. P2 asks the simplest possible tracking question: the channel jumps once, from setting A to setting B. How bad is a receiver that stopped learning (R2), and how long does a receiver that keeps learning (R3) need to recover, as a function of the step size μ? P3 then lets the channel move continuously up and down (a triangle wave in the coefficient `a`, one step of 2⁻⁷ every S symbols) and asks the project question: for which S does R3 stop keeping up, and which of three candidate channels leaves enough room to see it?

## 2. P2 — abrupt transition

**What the code does.** `p2_abrupt.py` trains all receivers for 30000 symbols on channel A, freezes R2, keeps adapting R3, and at symbol 50000 switches the channel to B for all receivers at the same instant (same bits, same noise). It repeats this for 100 seeds, three jumps (large: a 0.31→0.91, mid: 0.31→0.60, down: 0.91→0.31) and four step sizes, and averages the squared error and the error indicators over seeds.

**Why it is needed.** It is the cleanest way to see the *speed* of adaptation, separate from the noise LMS always has. It also tests the analysis tools (oracle, reference levels) on a case where the right answer can be computed.

**Predictions written before the run (nothing fitted).**
1. R2's error after the jump equals the formula 1 − 2wᵀp + wᵀRw for the old filter on the new channel.
2. R3's error falls back as a sum of decaying exponentials, one per direction of the filter space; the slowest direction decays with time constant 1/(2μλ_min), where λ_min is the smallest eigenvalue of R. So the recovery time should be proportional to 1/μ (slope −1 on a log–log plot).
3. The average coefficients move along (I − μR)ᵏ(w_A − w_B), i.e. exponentially towards the new best filter.

**What was measured.**
- R2: 0.3972 measured against 0.3965 predicted (large jump, μ = 2⁻⁸); 0.1126 against 0.1119 (mid); 0.692 against 0.7006 (down). This is 674 %, 309 % and 3185 % above what the best filter for the new channel achieves.
- Recovery time (kappa = 0.25): 1109, 2674, 5444, 10961 symbols for μ = 2⁻⁷ … 2⁻¹⁰ on the large jump; slope of log N_rec against log μ: −1.09, −0.98, −0.97. The prediction was −1.
- The area under the error-versus-time curve after the jump matches the model to within 0.7–7 %. The coefficient curves lie on top of the model (Fig. P2-coefficients).
- BER around the jump (μ = 2⁻⁸): after the large jump R1 has 15 % errors, R2 1.8 %, R3 0.18 % in the first 2000 symbols and 3·10⁻⁵ afterwards. After the mid jump R2's error power is about 4 times the minimum possible (309 % excess) but its BER is only 7.5·10⁻⁶ and R3 has no errors in 2·10⁶ bits: the MSE shows a large loss that the BER does not. This is why both metrics are reported.

**What success means.** The measured numbers agree with predictions made from the channel alone, so the oracle, the reference levels and the recovery-time definition can be trusted in the sweep.

**Unexpected results and what they meant.**
1. *Measured recovery time was up to 25 % longer than the model on the harsh channel.* The recovery time is defined as the last moment the noisy 64-symbol average is above a threshold; noise can only push that moment later. On the harsh channel the average is 3.6 times noisier than a plain Gaussian average would be (error values are correlated through the filter jitter). A simulation of the model plus this measured noise reproduces all 12 measured values (`p2_nrec_noise_check.py`). So the model is right and the statistic is biased upward; the report quotes the interval and the noise-free model value.
2. *R2 after the "down" jump at μ = 2⁻¹⁰ was 13 % better than predicted.* The filter had been trained on the harsh channel (a = 0.91), where one direction is weakly excited and learns slowly: after 30000 symbols it had not converged. The model started from zero weights predicts 0.6112, the measurement is 0.6124. The planned experiment trains at a = 0.31, where this does not happen (convergence in about 4800 symbols at the smallest μ against 30000 available; finding F-4). A design that trained at the harsh end would need about 60000 symbols.

**Viva points.** (1) Why the recovery time scales with 1/μ and with 1/λ_min. (2) Why a frozen filter's MSE after a jump can be computed with no simulation. (3) Why MSE can look bad while BER looks fine. (4) Why "last time above threshold" is a biased statistic. (5) MSE convergence does not mean every coefficient has converged.

## 3. P3 — continuous variation pilot

**What the code does.** `p3_run.py` runs, for three channels (control a 0.20–0.60; candidate A 0.50–0.90; primary 0.31–0.91), two SNRs (14, 16 dB), ten rates S = 1000 … 1 symbols per coefficient step, five step sizes μ = 2⁻⁶ … 2⁻¹⁰ and 20 seeds, all three receivers on identical data, and stores errors and error counts. `p3_analyse.py` computes, for every point, the oracle-normalized excess ε, the tracking fraction ρ (0 = no tracking loss, 1 = no better than a fixed averaged filter), pass/fail with a bootstrap interval, S*_MSE for three thresholds, S*_BER for three factors, S_cross, the selection criteria C1–C4, and a first look at the best μ for each S.

**Why it is needed.** The final sweep may only start once the channel, SNR and thresholds are chosen on independent pilot data (FREEZE-1). The pilot also shows whether the question can be answered at all: a boundary exists only if the tracking loss can be large (C1), the receivers can be told apart in BER (C3), and the pass/fail boundary lies inside the S grid (C4).

**Expected graph (written before the run).** ρ against S is an S-shaped curve: near 0 at slow S, rising towards about 1 at fast S; a smaller μ moves the rise to slower S; at the fastest S all μ curves meet near 1 (R3 can then only act as a fixed averaged filter).

**What was measured (Fig. P3-rho).** Exactly that shape, for every channel and SNR. On the primary channel at 14 dB the rate at which ρ crosses 0.5 is S*_MSE = 20, 20, 50, 50, 100 for μ = 2⁻⁶ … 2⁻¹⁰, and every pass/fail set is monotonic (180 of 180). S*_BER (factor 2) is 20, 50, 200, 200, 1000 — at the same S or slower, i.e. a stricter test. R3's BER stays better than both R1's and R2's at every S including S = 1, so no S_cross is observed within the grid.

**Selection rule result.** Only the primary channel satisfies C1–C4, at both 14 and 16 dB. The control channel and candidate A fail C1 (room to lose is too small: ε_plateau 0.60/0.98 and 0.51/0.85 against the required 1.0); the control also fails C3b (the frozen receiver makes fewer than 100 errors per 10⁷ bits at any S).

**Unexpected result and what it meant.** The literal wording of the static baseline ("the static S0 run") is ambiguous. If the static run uses the starting channel value, ρ at the slowest S is 0.20 for μ = 2⁻⁶ even though almost no tracking loss is expected, because LMS adds more noise on the harder part of the range (finding F-1). With a baseline that averages the static result over the channel values the trajectory visits, ρ is −0.01 there. For BER the effect is stronger: the literal static run has zero errors, so the criterion fails at nearly every S (S*_BER undefined). This is proposal P-12 and needs approval.

**What success means.** There is a measurable boundary with a monotonic pass/fail set, bracketed inside the grid, in both metrics, on one channel that meets all four criteria.

**Preview of the step-size trend (not a result).** The best μ for each S moves with the rate roughly as (1/S)^0.5 (slopes 0.49–0.59 over the unsaturated S values, statistical error about 0.01–0.02). This is between the two reference exponents (1/2 and 2/3) and does not yet separate them; a finer μ grid and the 100 final seeds are needed.

**Viva points.** (1) What ρ = 0 and ρ = 1 mean and why the plateau is the natural upper reference. (2) Why a boundary needs room to lose (C1). (3) Why S*_BER is at slower S than S*_MSE. (4) Why the choice of static baseline matters when misadjustment depends on the channel. (5) Why the pass/fail sets are checked for monotonicity.

## 4. Beginner explanations (added 20 Oct) — see `code/results/fig_explain_S_and_mu.png`

**Why smaller S means a faster channel.** The channel coefficient a[n] is a counter times 2⁻⁷. The counter moves by one step every S symbols. S is therefore the waiting time between steps, not a speed. Rate of change = 2⁻⁷/S per symbol: S = 1000 → slow (one tiny step per 1000 symbols), S = 10 → 100 times faster, S = 1 → changes at every symbol. A full up-and-down triangle takes 152·S symbols, so S = 10 sweeps the whole range in 1520 symbols, S = 1000 in 152000. (Panel 1.)

**What LMS does while the channel moves.** At each symbol the filter weights take a small step (size μ) to reduce the latest error. The ideal weights shift as the channel moves. LMS can only follow if it moves quickly enough, but every step also copies a little of the current noise into the weights.
- **Small μ:** smooth weights (little noise jitter) but slow — they lag behind the ideal weights (green curve, panel 2).
- **Large μ:** weights follow fast but jitter around the ideal (red curve).
- The error therefore has two parts, jitter (grows with μ) and lag (grows with the channel speed and with 1/μ). Total error is U-shaped in μ (panel 3), so each S has a best μ, and a faster channel (smaller S) needs a larger best μ. The L1 pilot preview gives best μ ∝ (1/S)^0.52 (not a result; the final 100-seed run and the fit rule decide).

**Reading the pilot.** Tracking stops being acceptable (ρ > 0.5) at S ≈ 14–20 for the largest μ and only at S ≈ 320 for the smallest μ: a small μ cannot keep up with a channel that a large μ tracks easily. The BER fails at about the same or a slightly faster S than the MSE because the frozen noise term hides the lag until the lag is several times the noise. For very fast channels (S ≤ 5) every μ is equally bad: the best LMS can do is act like a fixed filter for the average channel (ρ ≈ 1).

**Success / unexpected.** Success: smooth S-shaped ρ(S), bracketed S*, U-shaped ε(μ) with a bracketed minimum. Unexpected would be a non-monotonic pass set or a best μ at the grid edge; neither occurred for S ≥ 10. **Viva:** why S is a waiting time; lag–jitter trade-off; why the optimum μ shifts with speed; why a small-μ filter tracks a slow channel but fails a fast one.

## 5. Beginner explanations of the FREEZE-1 checks (added 20 Oct)
- **Why the training length is checked.** The filter learns like a ball rolling into a valley: the slowest direction needs about 1/(2μλ_min) symbols to settle. With λ_min = 0.63 and μ = 2⁻¹¹·⁵ that is about 2300 symbols, so 30000 symbols is 13 settling times: the remaining error is below one part in a million. Comparing with the Wiener (best possible) filter is how we know "converged" is true and not just assumed.
- **Why windows are whole triangle periods.** The channel climbs and descends. If a window stopped half way, one part of the range would be visited more than another and the averages would be biased. Whole periods visit every channel state exactly as the quasi-static weights assume (the check found zero deviation). Slow S (5000) needs one whole period = 760000 symbols.
- **What "BER reference resolved" means.** To compare R3's BER with a "no tracking loss" reference we must be able to measure that reference. If only 8 errors are expected, the reference is mostly noise. Rule: at least 100 expected reference errors. At 16 dB the equaliser is so good that errors are essentially absent for small μ, so the reference cannot be measured; at 12 dB there is plenty. That is why a lower SNR is used for BER only, and why simply lowering SNR was verified, not assumed (14 dB turned out only partly sufficient).
- **Why interpolation matters for BER.** BER grows by a factor of thousands between easy and hard channel states, so a straight line between measured points lies above the real curve; interpolating the logarithm follows it better. The independent slow-trajectory run confirmed this (agreement 0.96–1.02 against 0.90–0.97).
- **Viva:** settling time and λ_min; why a Wiener reference; whole periods; expected errors ≥ 100; log interpolation.
