# Stage P1 notes — floating-point static LMS (level L1)

Plain-language walk-through of what was built, why, what to expect on each graph, and what the measurements showed. All numbers are L1 simulation on pilot seeds (1000–1099). **No tracking result is claimed in P1.** Run everything with `python3 p1_validation.py` inside `code/` (about 10 s).

## 1. The picture in one paragraph
A random bit stream is turned into ±1 symbols (BPSK), passed through a short filter that smears each symbol into the next two (the ISI channel), and noise is added. Three receivers look at the same samples: R1 just checks the sign (no equalizer); R2 runs LMS during training and then freezes its 16 coefficients; R3 never stops adapting. LMS adapts by nudging each coefficient by μ × (error) × (input sample). If the channel stands still, the coefficients settle at the best possible filter (the Wiener solution). If the channel moves, the best filter moves, and LMS has to chase it. Project question: how fast can the channel move before the chase fails.

## 2. What each file does

| File | Role |
|---|---|
| `config.py` | Every parameter in one place (L = 16, Δa = 2⁻⁷, channel ranges, N_T, seeds). Status of each value written beside it |
| `lms_lib.py` | Bits, PRBS (LFSR), channel with moving coefficient, noise, the LMS loop for R2 and R3, error counting, the oracle, the exact formula for R1's BER |
| `pilot_analytic.py` | Pure-maths look at candidate channels at L = 16 (no randomness, no LMS) |
| `p1_validation.py` | The tests V0–V7, with pass/fail printed and figures saved |

Key idea for fairness: bits, noise and channel path depend only on the experiment seed, never on μ, Δ or L. Test V0 checks this.

## 3. The tests: purpose, expectation, measurement

| Test | What the code does | Why it is needed | Expected (from theory) | Measured | If it had gone wrong |
|---|---|---|---|---|---|
| V1 noise | 10⁶ noise samples: mean, variance, correlation, tails, seed repeatability | Every BER depends on the noise being right | Mean 0, variance exact, no correlation, 0.27 % beyond 3σ | Variance 0.31 % low, 0.276 % beyond 3σ, max autocorrelation 3·10⁻³ (limit 4·10⁻³), repeatable | BER curves would be shifted for no visible reason |
| V2 flat BER (Fig. V2) | No ISI, 12 SNR points, 2·10⁶ bits each, compared with Q(√(2Eb/N0)) | Checks noise scaling, threshold, bit counter and the SNR definition together | Points on the theory curve | 11 of 12 inside 95 % interval, 12 of 12 inside 99 % (one point at 95 % is expected by chance) | A shifted curve = wrong σ; flat floor = alignment bug |
| V2b static ISI (Fig. V2b) | Fixed channel a = 0.60 and a = 0.91, R1/R2/R3 BER vs Eb/N0 | Shows the problem equalization solves | R1 shows an error floor on the closed-eye channel; equalizers remove it | R1 at a = 0.91 stays near 14–20 % at every SNR, R2/R3 fall to 0 errors in 10⁶ bits at 16 dB. R1 matches the exact formula | If R3 were not better, the LMS or alignment would be wrong |
| V3 alignment | Correlates hard decisions with transmitted symbols at different lags | Wrong alignment gives BER ≈ 0.5 from a perfect equalizer | Peak at lag Δ for R3, 0 for R1 | Peak at lag 2 and 0; wrong delays give BER 0.499–0.503 | Reported BER would be meaningless |
| V4a coefficients | Average LMS coefficients after convergence vs the Wiener solution | Proves LMS finds the right answer on a static channel | Equal within a few percent | 0.17–0.18 % (Fig. V4) | Update sign or error definition wrong |
| V4b excess MSE | Measured extra MSE vs textbook formula | Checks the misadjustment theory used to think about μ | Within 20 % | **Fails**: measured is 1.48× the formula at three μ values (finding F-1) | See below |
| V4c control | Same measurement on a white-input flat channel, and scaling with μ | Separates "my measurement is wrong" from "the formula does not fit" | Formula exact; excess halves when μ halves | Formula matches within 4 %; ratios 2.05 and 2.02 | — |
| V5 delay (Fig. V5) | MSE vs decision delay Δ, oracle and LMS | Δ must be chosen, not assumed | A broad minimum, steep rise near Δ = 17 | Flat for Δ up to about 12 (control) or 8 (primary); Δ = 2 chosen by the 2 % rule | Δ = 0 would be a hidden mistake on some channels |
| V6 PRBS | Period, balance, autocorrelation; LMS trained on PRBS vs on 0,1,0,1… then tested on random data | Training must excite every direction of the filter space | PRBS-trained MSE ≈ oracle; alternating-trained much worse | PRBS 0.0281 (oracle 0.0274); alternating 0.9645 | A periodic training pattern would look fine and fail on payload |
| Learning curves (Fig. P1) | MSE vs time while training | Checks N_T is long enough | Larger μ converges faster | Within 10 % of final after 965, 1392, 2378, 4009 symbols for μ = 2⁻⁷…2⁻¹⁰ | Short training would leave R2 badly trained |
| V7a oracle | Builds the oracle at an instant, then re-derives it by brute force (300 000 random trials using the system equation) on a fast ramp where the channel moves inside the filter window | The oracle is the yardstick for tracking loss, so it must be right | Brute-force MSE equals oracle value | 0.04177 vs 0.04190 (−0.32 %); coefficients differ 0.11 %; an oracle that ignored motion inside the window would lose 1.83 % | A wrong yardstick makes every later ε meaningless |
| V7b oracle floor | Real R2/R3 MSE compared with the oracle at three rates | The oracle is a lower bound; nothing real may beat it | MSE ≥ oracle | R3 and R2 both above at S = 1000, 200, 50 | Would mean a bug in oracle or MSE |

### What the unexpected result (V4b) means — investigated, explained
**Short answer.** The textbook formula quietly assumes that the error left over after the best possible filter is "white": each error is unrelated to the previous one. On a flat channel that is true and the formula works (measured/formula = 0.996). On an ISI channel the leftover error is mostly leftover interference from neighbouring symbols, so consecutive errors are strongly related (correlation −0.53 between neighbours). LMS corrects the filter after every error. When the next error tends to have the opposite sign to the last one, the correction made for the last error is partly wrong for the next, so the filter jitters more in the output than the formula expects. A model that includes this correlation predicts 1.468 times the textbook value; the measurement is 1.468–1.480.

**What was checked (nothing in the algorithm, the 20 % tolerance or the measured numbers was changed).**
- *Code:* a plain-python LMS and an independently written one give identical errors (difference 1e-15 and 0); delay alignment is exact; the fixed best filter measures 0.9994 of the theoretical minimum MSE; the steady-state window is flat. So not a bug.
- *Measurement:* 16 independent seeds of 10⁶ symbols; 95 % intervals on the ratio are ±0.003–0.004. Not noise, not a short run.
- *Is it the input correlation matrix?* No. The eigenvalue form of the formula differs from the trace form by 1–2 %. The eigenvalue spread (0.28 to 2.88) is not the cause.
- *Is it the residual error?* Yes. Shuffling the time order of the data (which removes the correlation but keeps everything else) brings the ratio to 0.99–1.00. Gaussian data does not remove it. Adding ISI step by step moves the ratio smoothly from 1.00 (flat) to 1.75 (a = 0.9), tracking the lag-1 correlation.
- *Left over:* 1–6 % (at μ = 2⁻¹⁰…2⁻⁸) between measurement and the first-order model; it halves as μ halves, so it is a second-order-in-μ effect, not modelled here.

**Classification:** incorrect use of a theoretical approximation. Not a bug, not a measurement issue.

**Expected graph for the report (Fig. M1).** Left: ratio measured/textbook versus ISI strength; prediction (model) is a line, measurements are dots with error bars. Middle: gradient-noise correlation by lag (large at lag 0, negative at lag 1). Right: residual-error autocorrelation by lag.

**Consequence for the project.** The measured static baseline is used in the tracking metric, so definitions are unchanged. But the textbook formula must not be used for numerical predictions of the best μ on the primary channel (it would underestimate the noise cost by up to ~1.75×); the correlated-error model is the reference there.

**Viva points.** (1) State the three assumptions behind the misadjustment formula and which one fails. (2) Why gradient noise at lag 0 is as the textbook says but lags ≥ 1 are not zero. (3) Why a shuffled-data run is a good control. (4) Why the excess is still linear in μ (first order). (5) Why we kept the failed test and added a separate reference test.

## 4. What the analytic pilot says (L = 16, Eb/N0 = 14 / 16 dB)
Question: is there enough room to see tracking fail? Failure cannot cost more than what a single fixed filter for the average channel loses (the "plateau"), because the channel path is bounded. Plateau excess over the oracle: control 0.60 / 0.98; primary 1.13 / 1.83. The primary channel clears the "plateau ≥ 1" measurability test at both SNRs; the control does not clear it at either SNR (0.60 and 0.98). Direct detector error rate on the primary channel at the top of the range is about 14–15 % at both SNRs (closed eye).

## 5. Concepts to be able to explain in the viva
1. **BPSK, Eb/N0 and σ²:** x = ±1, Eb = 1, σ² = 1/(2·Eb/N0); BER = Q(√(2Eb/N0)).
2. **ISI and the eye:** r = x + a·x₁ + 0.1·x₂ + noise. The decision is wrong without noise if a + 0.1 ≥ 1.
3. **LMS in one line:** w ← w + μ·e·u, a noisy step down the error bowl. Large μ: fast but jittery. Small μ: smooth but slow.
4. **Wiener solution w = R⁻¹p:** the best fixed filter. Oracle MSE is its value for the current channel.
5. **Decision delay Δ:** the equalizer estimates x[n−Δ]; a causal FIR cannot always undo a channel in zero delay.
6. **Persistent excitation:** training data must contain every direction; a PRBS is the standard cheap choice. The received-signal correlation matrix is R ≈ HHᵀ + σ²I, not the identity.
7. **Misadjustment (excess MSE):** the price of the jitter; proportional to μ; 1.47 × the textbook value on this channel because the leftover error is correlated (white-error assumption fails).
8. **Why an oracle:** it separates "the noise LMS always has" from "the lag from a moving channel".

## 6. What comes next
P2: abrupt transition (MSE vs time, reacquisition vs μ, coefficient trajectories), then P3 continuous variation and the pilot selection of the primary channel, FREEZE-1 on 22 Oct.
