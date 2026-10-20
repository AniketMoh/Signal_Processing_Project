# Comprehensive project audit — PPR-22 versus the current implementation (20 Oct 2026)

Scope: everything up to and including the FREEZE-1 preparation. **No existing code, parameter or result was modified for this audit.** Four small, separate audit checks were run (new files in `code/audit/`, outputs in `code/results/audit_*`); none of them reruns an experiment. All numbers are **L1** (floating-point simulation) and **pilot** unless stated.

**Evidence labels used throughout**
- **[M] mathematically verified** — follows from a derivation or exact calculation that has been checked.
- **[E] experimentally tested** — measured in simulation with stated seeds and sample sizes.
- **[A] assumed** — not yet tested; stated so it can be challenged.

**Execution flow diagram (single figure):** `code/results/fig_audit_execution_flow.png` (source `code/audit/execution_flow.dot`). It shows the path from configuration to transmitter, channel and noise, the three receivers on the same received samples, the measurement window, and the analysis. Dashed boxes are analysis-only quantities (oracle, plateau) that no receiver ever sees.

---

## 0. Summary

**Overall verdict.** The simulation core is correct as far as it has been tested.
- **Same LMS loop everywhere:** one LMS loop serves P1, P2, P3 and the sweep.
- **Correct receivers:** the three receivers get identical received samples, R2 stops at N_T and R3 keeps adapting.
- **Correct reference and scaling:** R3 learns from the true symbol (supervised), and the noise is Gaussian and correctly scaled.
- **Correct oracle:** the oracle is an analytic calculation and is exact for a channel that moves inside the equalizer window.

The issues found are about **statistics, bookkeeping and unfinished commitments**, not about the LMS equations.

**Six most important findings**
1. **BER intervals:** bit errors come in short bursts, so plain Wilson intervals are somewhat too narrow.
   - Re-analysing the pilot with the measured burst factor changes 31/252 (16 dB) and 9/252 (14 dB) statuses, all from "pass" to "inconclusive" except one "fail" to "inconclusive".
   - It changes **no** S*_BER value.
   - The BER reference's own sampling uncertainty is currently ignored (section B, items B-1 and B-2).
2. **Gaussian tail validity:** the Gaussian generator is now validated down to BER 2.7·10⁻⁷ (new check). The earlier V2 only reached about 10⁻⁴. L1 BER below 10⁻⁴ is therefore defensible when enough errors are counted (B-10).
3. **Bounded hardware noise model:**
   - MSE is unchanged (≤ 0.3 %).
   - R3 BER changes by about 10 % where it can be resolved.
   - The direct detector R1 changes 11× at low BER.
   - L1 results stand as the **Gaussian reference**. Hardware BER needs the FPGA noise model in L2 (B-11).
4. **Gaps in the final plan:**
   - The **control channel is missing from the FREEZE-1 final sweep**, although D-03 keeps it as the control (B-8).
   - The **final P2 "down" step trains on the harsh channel**, where 30000 symbols are not enough for μ = 2⁻¹⁰ (finding F-4) (B-15).
5. **Analysis-code problems:** the **S_cross output is computed with the wrong rule** (a reporting bug, B-4). The **exponent confidence interval is underestimated** (B-5).
6. **Classification revised under the stricter definitions you asked for:** **4 genuine contradictions** remain:
   - the AI-disclosure sentence;
   - R ≈ σ²I;
   - "grows without bound";
   - the midterm P1–P6 schedule.

   Everything else is a justified methodological change, an extension or an unfinished commitment (section C). My earlier list of 9 counted several justified changes as contradictions. That was too broad.

---

# A. Code walkthrough (for a beginner)

## A.1 Main files

| Stage | Entry script | What it does | Shared library functions it calls |
|---|---|---|---|
| Parameters | `config.py` | All constants: L = 16, M = 3, Δa = 2⁻⁷, N_T = 30000, channel ranges, seeds; `sigma_from_ebn0` (lines 31–33) | — |
| P1 | `p1_validation.py` | Static-channel tests V0–V7 (reproducibility, noise, BER vs theory, alignment, LMS vs Wiener, Δ sweep, PRBS, oracle) | `lms_lib.make_experiment` (145–163), `lms_lib.run_receivers` (166–171) → `lms_lib.lms_receivers` |
| P1 (F-1) | `investigate_misadjustment.py`, `misadj_lib.py` | The 1.47× misadjustment investigation | `misadj_lib.wiener`, `exact_C`, `lms_rows` |
| P2 | `p2_abrupt.py` | Abrupt jump A → B, recovery time N_rec | `exp_lib.step_counter` (30–34), `exp_lib.make_exp_from_counter` (19–27), `exp_lib.run_lms` (37–39) → `lms_receivers`; `n_rec_from` (30–43) |
| P3 pilot | `p3_run.py`, `p3_analyse.py` | Triangle variation, 3 channels, pilot statistics | `triangle_counter`, `make_exp_from_counter`, `run_lms`, `ber_indicators`, `oracle_J_series` |
| Grid pilot / final | `sweep.py`, `grid_pilot.py`, `sweep_analyse.py`, `freeze_grids.py` | The engine for the final sweep and its analysis | `sweep.run_point` (17–27), `sweep.run_sweep` (30–52), `sweep_analyse.analyse` (51–143) |

## A.2 Execution sequence (follow the diagram top to bottom)

1. **Bits.** Training bits come from the LFSR (`lms_lib.lfsr_bits`, lines 22–32; polynomial x¹⁵ + x¹⁴ + 1, seed 1). They are the same for every seed. Payload bits come from `make_bits(n, seed)` (lines 16–19, numpy generator).
2. **BPSK:** x = 2b − 1 (`bpsk`, lines 35–37).
3. **Channel state:** the integer counter c[n] is fixed at c_lo during training, then follows the triangle (`triangle_counter`, 41–53). Taps are [1, c[n]·2⁻⁷, 0.1] (`taps_from_counter`, 56–62).
4. **Channel:** r[n] = Σ_k h[k,n]·x[n−k] (`apply_channel`, 65–71).
5. **Noise:** v[n] = σ·N(0,1) with σ² = 1/(2·Eb/N0) (`make_noise`, 74–76; `sigma_from_ebn0`, config 31–33). It is added to r.
6. **Receivers.** R1 takes the sign of r[n]. R2 and R3 come from a single call to `lms_receivers` (80–127).
7. **Measurement** (`sweep.run_point`, 17–27). Squared errors and error indicators are averaged or counted **only from n = N_T onwards**.
8. **Analysis** (`sweep_analyse.analyse`). The oracle, ε, ρ, BER status, S*_MSE, S*_BER, S_cross and μ_opt are computed here.

## A.3 The LMS update (exact code, `lms_lib.py` lines 104–123)
```python
ya = 0.0
for k in range(L):
    ya += wA[k] * u[k]                 # y[n] = w[n]^T u[n]
...
ref = d[n]                             # supervised: true symbol x[n-Delta]  (mode 0)
e = ref - ya                           # a-priori error
...
for k in range(L):                     # LMS update: w = w + mu * e * u
    wA[k] += mu * e * u[k]
```
This is exactly PPR-22 Eq. (7) with Eq. (11), e[n] = x[n−Δ] − y[n] **[M]**.

Two independent re-implementations agree with it: a plain-Python loop (difference 8.9·10⁻¹⁶) and a row-based LMS (difference 0.0) **[E]** (`MISADJUSTMENT_DERIVATION.md` §5). The SHA-256 of `lms_lib.py` is recorded in `results/original_V4b_preserved/`.

## A.4 Identical inputs for R1, R2 and R3 **[M, E]**
- **Same samples by construction:** R1 uses `exp["r"]` directly (`exp_lib.ber_indicators`, line 45). R2 and R3 are computed in the same loop from the same delay line `u`, which is filled from the same `r[n]` (`lms_receivers`, lines 98–100). So all three receivers see the same samples **[M]**.
- **Data does not depend on receiver settings:** bits, trajectory and noise depend only on (seed, S, channel, Eb/N0), never on μ or Δ (docstring of `make_experiment`, 146–147). Test V0 checks that the same seed gives identical r and that receiver settings do not change the data **[E]** (V0 PASS).

## A.5 R2 frozen, R3 adapting **[M]**
```python
if n == N_T:                           # freeze: w_F = w[N_T]   (lines 101-103)
    for k in range(L):
        wF[k] = wA[k]
...
if n < N_T: yf = ya                    # during training R2 = R3
else:       yf = sum(wF[k]*u[k])       # afterwards R2 uses the frozen copy (107-112)
```
`wF` is written in exactly one place, so R2 never changes after N_T. `wA` is updated at every n (line 122).

## A.6 Adaptation mode
- **Supervised only so far.** R3 uses **supervised evaluation** (`mode = 0`): the error uses the true symbol. Every result so far uses `mode = 0` (`exp_lib.run_lms`, line 37, default; `sweep.run_point`, line 23).
- **Matches the report.** PPR-22 Sec. 5.6 permits supervised mode for controlled experiments, provided it is labelled. It is labelled in all documents.
- **Decision-directed mode exists but is untested.** The code is at lines 113–114 (`ref = sign(ya)`) but has **never been run or tested**. Pilot-assisted mode does not exist.

## A.7 How L = 16, Δ = 2 and N_T = 30000 were chosen
- **L = 16.** This is PPR-22's own value (Table 3: "L = 16, M = 3"), adopted as a project decision (D-07). New audit check (`audit/gauss_tail_and_L_check.py`): the analytic best possible MSE at the hardest channel state (c = 116, 16 dB) is
  - 0.04901 at L = 8, 0.03591 at L = 12, **0.03464 at L = 16**, 0.03451 at L = 20, 0.03450 at L = 32.
  - L = 16 is therefore within 0.4 % of an infinitely long equalizer, while L = 12 is 4 % worse **[M]**.
- **Δ = 2.** Chosen by the rule in `p1_validation.choose_delta` (lines 109–121): the smallest Δ whose oracle MSE is within 2 % of the best Δ at every channel state of the primary trajectory and at both pilot SNRs. Worst case 1.34 % **[M]** (V5 PASS). The oracle's own best Δ is 3–6 depending on the case. The MSE curve is flat, which is why a stated rule is used instead of the bare minimum.
- **N_T = 30000.** Check `check_NT.py` (40 seeds, c = 40, 16 dB, the slowest case) **[E]**:
  - The slowest mode has λ_min = 0.628, so the time constant at μ = 2⁻¹¹·⁵ is 1/(2μλ_min) = 2308 symbols. 30000 symbols is 13 time constants.
  - The distance of the mean weights from the Wiener filter at N_T is 2.8·10⁻⁶ of ‖w_o‖² (model 1.0·10⁻⁶).
  - **Sufficient for every μ in the grid**, for training at c = 40.

## A.8 N_T for the smallest μ — answered in A.7
Training only ever happens at c_lo = 40 in the tracking sweep, so that is the relevant check.

**Exception:** the P2 "down" step trains at c = 116, where 30000 symbols are **not** enough at μ = 2⁻¹⁰ (F-4: about 60000 needed). See B-15.

## A.9 PRBS and other random sources
| Signal | Generator | Matches PPR-22? |
|---|---|---|
| Training sequence | **LFSR**, x¹⁵ + x¹⁴ + 1, period 32767 (`lfsr_bits`). V6: 16384 ones per period, off-peak autocorrelation exactly −1/32767 **[E]** | Yes (Sec. 5.4; polynomial and length reported) |
| Payload bits | numpy `default_rng(seed).integers` (PCG64) | PPR-22 does not specify (the payload will be audio or image) |
| Noise | numpy `default_rng(seed + 500000).standard_normal` (exact Gaussian) | Not the LFSR sum-of-uniforms of Sec. 4.3; that generator belongs to the hardware levels (section B.2) |

## A.10 Time-varying channel (exact code, `triangle_counter`, lines 45–53)
```python
c = np.full(n_total, c_lo)            # static during training
k = (n - N_T) // S                    # number of +1 steps so far: one every S symbols
idx = k % (2 * steps)                 # position inside one up-down period
c[N_T:] = c_lo + np.where(idx <= steps, idx, 2*steps - idx)
```
a[n] = c[n]·2⁻⁷. One full period is 2·(c_hi − c_lo)·S = 152·S symbols, and the rate of change is 2⁻⁷/S per symbol. **A smaller S means a faster channel.** P2 uses `step_counter` instead (exp_lib 30–34).

## A.11 Independence from the FPGA architecture **[M]**
`lms_receivers` is the mathematical algorithm. Nothing in L1 models a datapath, clock, pipeline or word length. A search of the code finds no shared-MAC or time-multiplexed implementation, only document text.

Integer addition is associative. A parallel adder tree and a sequential MAC therefore give identical L2 results as long as there is no intermediate rounding or saturation. **No L1 result depends on the architecture.**

---

# B. Validation report

Severity: **High** = could invalidate a headline result; **Medium** = affects an interval, a claim or a commitment; **Low** = presentation or bookkeeping.

## B.1 Issues table

| # | Issue | Evidence | Severity | Recommended correction |
|---|---|---|---|---|
| B-1 | Bit errors are not independent, so plain Wilson intervals are too narrow | `check_error_independence.py`: P(error at n+1 \| error at n) = 0.05–0.29 against BER 10⁻⁵–10⁻³; mean burst size 1.07–1.22 (μ ≤ 2⁻⁷) and 1.7–1.9 (μ = 2⁻⁵) **[E]** | Medium | A-4 (burst-adjusted Wilson) plus a seed-level bootstrap cross-check |
| B-2 | The BER reference is treated as exact in the threshold f × BER_ref (`sweep_analyse` line 91) | A resolved reference (≥ 100 errors) still has about 10–14 % relative standard error (with bursts) **[M]** | Medium | Add a paired seed-bootstrap check of the ratio BER_R3 / BER_ref (B.3.9) |
| B-3 | At 16 dB the BER reference cannot be measured for μ ≤ 2⁻⁶ | `ber_static_analysis_log.txt`: 0.0–18.8 expected reference errors per final window **[E]** | Medium (documented) | Option A, already approved: BER study at 12 and 14 dB |
| B-4 | **S_cross reporting bug:** the code stores the *smallest S with a significant advantage* (`sweep_analyse` line 104 `S_cross_min = min(cross)`, printed at line 113), not "the S at which R3 ceases to outperform" | Code reading **[M]**. Affects only μ = 2⁻⁵ at 16 dB in the pilot, where R3 loses its advantage between S = 5 and S = 2 | Low–Medium | Bug fix: report the fastest S at which R3 is still significantly better and the first S at which it is not; keep "no S_cross observed within the grid" |
| B-5 | The exponent confidence interval is underestimated: bootstrap 95 % [0.52, 0.52] at 16 dB | Only seed noise is resampled. The grid spacing, the parabolic refinement and the choice of S range are not **[M]** | Medium for the exponent claim | Report fit-range and refinement sensitivity next to the bootstrap; treat the exponent as a hypothesis test, not a precise number |
| B-6 | The oracle is not a strict mathematical lower bound for LMS | LMS weights depend on past data that overlap the current window, while the oracle is a fixed-per-time linear filter **[M]**. Measured MSE never fell below the oracle: V7b and every grid-pilot point show ε > 0, minimum 1.5 % (14 dB) and 2.0 % (16 dB) **[E]** | Low | Describe it as "best fixed linear filter with channel knowledge", not "absolute bound" |
| B-7 | ρ can exceed 1 | ε_plateau is quasi-static and analytic (`plateau_stats`). ρ up to 1.14 for small μ and up to 4.45 for μ = 2⁻⁵ at S = 1: LMS noise plus lag makes R3 worse than a fixed averaged filter **[E]** | Low | Explain ρ > 1 in the report |
| B-8 | **Control (mild) channel not in the FREEZE-1 final sweep** | D-03 keeps it as the control; `FREEZE_1_PROPOSED.md` §2 lists only the primary channel | Medium (commitment) | Add the control channel to the final sweep (about 10 min per SNR) |
| B-9 | Seed overlap in the proposed 14 dB BER study (seeds 6000–7499) | V2 uses payload streams 7000–7011 (`test_V2`, line 86) **[M]** | Low | Use seeds 100000–101499 |
| B-10 | Is L1 BER below 10⁻⁴ trustworthy? | V2 only reached about 1.3·10⁻⁴. New check: flat channel, 4·10⁸ bits per point, measured inside the exact 95 % interval of theory at 9, 10 and 11 dB (BER 3.3·10⁻⁵, 3.8·10⁻⁶, 2.7·10⁻⁷; 13336, 1501 and 108 errors) **[E]** | Resolved | Report this as test V2c |
| B-11 | A bounded (hardware-style) noise model changes BER tails | `audit/noise_model_check.py` (B.2.9) **[E]** | Low for L1, Medium for hardware | L1 results are the Gaussian reference; L2 adds the FPGA-compatible noise model |
| B-12 | The earlier P3 S*_BER list (20, 50, 200, 200, 1000…) mixed observed and upper-bound values | Already recorded in DECISIONS | Low | Indicative only; superseded by the grid pilot and the final analysis |
| B-13 | N_rec definition changed from PPR-22 (pre-transition level) to the post-transition level | D-09 | Low–Medium | Also report PPR-22's literal definition where it is defined (sensitivity) |
| B-14 | Non-minimum-phase preset promised in PPR-22 Sec. 5.3 is absent | All channels [1, a, 0.1] are minimum phase (roots −0.13 and −0.78 at a = 0.906) **[M]** | Medium (commitment) | One static P1 test with h = [0.5, 1.0] showing why the Δ sweep is needed |
| B-15 | **Final P2 "down" step (c 116 → 40) trains at c = 116**; R2 does not converge for μ = 2⁻¹⁰ in 30000 symbols | F-4 (R2 measured 0.6124 against the converged value 0.7006) **[E]** | Medium | Either N_T = 60000 for that step only, or keep 30000 and report R2 as "frozen before convergence" |
| B-16 | Static baseline runs reuse the trajectory seeds | `sweep.run_sweep` uses the same seed list. Same payload and noise, so the runs are **paired, not independent** **[M]** | Low (useful) | Never use an independent two-sample test between them; use pairing (B.3.9) |
| B-17 | A-1 (log interpolation) and A-4 are not yet implemented | `sweep_analyse` line 75 uses linear `np.interp` | Medium (must be done before the final analysis) | Implement after approval |

## B.2 Noise generation and the 10⁻⁴ limit (your section 2)
1. **How noise is generated:** `lms_lib.make_noise` (74–76): `sigma * np.random.default_rng(seed).standard_normal(n)`, called with seed + 500000.
2. **Genuinely Gaussian.** numpy's standard normal generator is exact, not approximate. V1 checks mean, variance (error −0.31 %), autocorrelation (≤ 3·10⁻³ against a limit of 4·10⁻³), P(\|v\| > 3σ) = 0.00276 against 0.00270, and repeatability **[E]**.
3. **Generator:** numpy PCG64 bit generator with the ziggurat normal method.
4. **Correct scaling.** σ² = 1/(2·Eb/N0) with Eb = 1 for ±1 symbols (config 31–33) **[M]**. V2 (12 points, 0–8.25 dB) and the new V2c (9–11 dB) match Q(√(2Eb/N0)) **[E]**. Note that Eb/N0 refers to the transmitted symbol energy; the channel adds energy 1 + a² + 0.01 (D-08).
5. **Does the bounded-support limit apply to L1? No.** It is a property of the planned LFSR sum-of-12-uniforms generator, whose tails stop at ±6σ. L1 does not use that generator.
6. **Why we report BER below 10⁻⁴.**
   - With Gaussian noise, a BER is scientifically defensible when enough errors are counted, whatever its size.
   - The generator's tail is now validated to 2.7·10⁻⁷ (B-10).
   - Below roughly 10–100 errors a value is only an estimate with a wide interval. With zero errors only an upper bound is reported (B.3.11).
7. **Not a violation.** PPR-22's 10⁻⁴ sentence describes the hardware generator. This is recorded as D-12: dashed 10⁻⁴ line on every L1 BER figure, plus one sentence in the report.
8. **Should Gaussian-reference and FPGA-compatible results be distinguished? Yes.** L1 = Gaussian reference. L2 and later = FPGA-compatible noise. They must never be mixed in one curve without a label.
9. **Effect of the noise model.** Small controlled comparison `audit/noise_model_check.py`: 14 dB, 40 seeds, bounded model = sum of 12 uniforms (LFSR bit correlations not modelled) **[E]**.
   - **Tail probability above tσ** (bounded / Gaussian): t = 3: 0.75×; t = 4: 0.27×; t = 4.5: 0.08×; t = 5: 0.007× **[M]**.
   - **MSE of R2 and R3:** identical within 0.3 % in all 12 cases. MSE depends only on the variance.
   - **R1 BER:** identical when ISI dominates (c = 116: 0.151; triangle: 0.027). **11× lower** at c = 40 static (3.6·10⁻⁶ → 3.3·10⁻⁷), where only the noise tail causes errors.
   - **R3 BER:** where at least 100 errors are counted, the change is 0.90–1.05× (e.g. c = 116, μ = 2⁻⁶: 2344 → 2100 errors). The equalizer output adds 16 noise samples, which is close to Gaussian again.
   - **Conclusion:** S*_MSE is unaffected. BER ratios (R3 against its own reference) should move much less than absolute BER, but this is **[A]** until tested in L2.
10. **Can a small controlled comparison be done? Yes, and it was done** (item 9). A version with the actual LFSR bit streams belongs to L2.
11. **What needs rerunning? Nothing at L1.** Hardware-level BER claims will need L2 runs with the FPGA noise model.

## B.3 BER calculation and error dependence (your section 3)
1. **BER calculation** (`exp_lib.ber_indicators`, 42–49):
```python
e1 = ((r >= 0) != bits)                        # R1: decision on r[n] vs bits[n] (delay 0)
ref[DELTA:] = bits[:n - DELTA]                 # R2/R3 compare with bits[n - 2]
e3 = ((yA >= 0) != ref)
```
   BER = (sum of indicators over the window) / (number of bits), pooled over seeds (`sweep_analyse`, lines 77–81).
2. **Training is excluded:** every count uses `[n_t:]` (`sweep.run_point`, line 26) **[M]**.
3. **Why errors are correlated although the noise samples are independent.**
   - The equalizer output noise is Σ_k w_k·v[n−k]. Consecutive outputs share 15 of their 16 noise samples, so the output noise is correlated in time.
   - The residual ISI depends on a group of neighbouring symbols, and a bad pattern affects several consecutive decisions.
   - In a moving channel, errors also concentrate where the channel is hardest or the lag is largest.

   The noise is independent. **The errors are not.**
4. **Test used:** `check_error_independence.py`.
   - P(e[n+1] = 1 | e[n] = 1) compared with the BER.
   - Bursts formed by merging errors less than 20 symbols apart, giving errors per burst.
   - The per-seed dispersion index.
5. **Why Wilson is too narrow.** Wilson assumes k independent errors. With bursts of mean size m, there are only about k/m independent events, so the true variance is about m times larger.
6. **Audit of A-4 (burst-adjusted Wilson): interval = m̄ × Wilson(C, N).**
   - Assumes **[A]** that bursts are independent of each other. This is plausible because they are separated by more than the 16-tap memory.
   - Assumes **[A]** that the burst size does not depend on the count.
   - Assumes **[A]** that a gap of 20 captures the dependence. The conditional probability at lag 2 already falls to 0.00–0.17, so this is reasonable.
   - Uncertainty in m̄ is ignored.
   - Uneven error rates across the window **do not** widen the interval: a sum of Bernoulli variables with unequal p has variance ≤ N·p̄(1−p̄) **[M]**.
   - **Weakness:** the gap value is a choice, so a sensitivity check with gaps of 10 and 40 is recommended.
7. **Seed-level bootstrap.** Justified, because seeds are independent replicates (next item). It makes no burst assumption.
   - **Limitation:** with about 1 error per seed and many zeros, percentile intervals under-cover. Use it as a cross-check only where the total exceeds about 100 errors.
8. **Seeds are independent runs [M].**
   - Each seed has its own payload stream `default_rng(seed)` and noise stream `default_rng(seed + 500000)`. PCG64 with SeedSequence makes different seeds statistically independent.
   - Streams would collide only for seeds ≥ 500000, which are never used.
   - The training sequence and the channel trajectory are the same for all seeds by design. They are fixed experimental conditions, not random.
9. **Paired seed-level bootstrap for R3 against its static reference.**
   - The static runs use the **same seeds** as the trajectory runs, so they are paired.
   - Resample the seed indices with replacement, B = 2000 times. In each resample:
     - recompute the pooled R3 errors in the trajectory window;
     - recompute the pooled static errors at the 11 channel states for the same seeds;
     - form BER_ref (interpolated and occupancy-weighted) and the ratio BER_R3 / BER_ref.
   - The 2.5 % and 97.5 % percentiles of the ratio give the interval. Pass if the upper limit < f, fail if the lower limit > f.
   - This includes the reference's own uncertainty (fixes B-2) and the burst dependence automatically.
   - It needs enough errors on both sides (about ≥ 100 in total each).
10. **Are 100 seeds enough?** Expected reference errors per final window with 100 seeds (`ber_static_analysis_log.txt`) **[E]**:
    - 12 dB: ≥ 297 for every μ, enough.
    - 14 dB: 124 at μ = 2⁻⁶·⁵, 8–53 for μ ≤ 2⁻⁷, hence the approved 1500-seed study.
    - 16 dB: ≤ 19 for μ ≤ 2⁻⁶, which would need 10⁹–10¹¹ bits.

    Rare BER at 16 dB is **not** measurable with any feasible seed count for small μ.
11. **Zero-error runs.**
    - Report "0 errors in N bits, 95 % upper bound 3/N" (rule of three; Wilson gives about 3.84/N).
    - Never report BER = 0.
    - In figures, show an arrow at the upper bound.
    - Log interpolation cannot use zeros. Those cases fall back to linear interpolation with upper bounds and are labelled reference-limited.
12. **Is pass/fail/inconclusive justified?**
    - **Per point, yes:** a 95 % two-sided interval gives at most about 2.5 % chance of a wrong P or F at the threshold.
    - **Across 252 points, a few misclassifications are expected by chance** (multiple comparisons). Two rules protect S*: an inconclusive point counts as not passing, and S*_BER requires demonstrated monotonicity.
    - **Not yet justified:** the reference uncertainty (B-2) and the bursts (B-1). A-4 plus the paired bootstrap fix both.
13. **Do earlier BER boundaries change?** Re-analysis of the grid pilot with burst factors (D = 1.9 for μ ≥ 2⁻⁶, D = 1.25 for μ ≤ 2⁻⁶·⁵; approximation, `audit/ber_deff_sensitivity.py`) **[E]**:
    - 16 dB: 31/252 statuses change. 14 dB: 9/252.
    - All changes are p → ? except one F → ?.
    - **No S*_BER changes.** 16 dB μ = 2⁻⁵: 5. 14 dB μ = 2⁻⁵: 5. 14 dB μ = 2⁻⁵·⁵: 10.
14. **Valid against indicative (all L1 pilot, 20 seeds).**
    - **Valid, pending the final run:**
      - every **fail** at fast S;
      - S*_BER = 5 (μ = 2⁻⁵, 14 and 16 dB) and 10 (μ = 2⁻⁵·⁵, 14 dB), which have a resolved reference and are unchanged under the burst adjustment;
      - "R3 beats R1 and R2 at every S" for μ ≤ 2⁻⁵·⁵. The differences are orders of magnitude, so the result is robust to the interval method.
    - **Indicative only:**
      - all lower-case "p" (conditional) passes;
      - the old P3 S*_BER list;
      - the μ = 2⁻⁵ S_cross statement (B-4).

## B.4 Oracle, MSE and tracking boundaries (your section 4)
1. **Oracle code** (`exp_lib.oracle_J_series`, 63–78). For each n it builds the 16 × 18 matrix H, whose row j uses the taps active at n − j. Then:
```python
p = Hm[:, :, DELTA];  R = Hm @ Hm^T + s2*I;  w = solve(R, p);  J_or = 1 - p.w
```
2. **It is pure analysis.** The oracle is never in the data path and is not a fourth receiver **[M]**. On hardware it would not exist.
3. **It assumes knowledge of the true channel taps, the noise variance and i.i.d. ±1 symbols.** It is a "genie" reference.
4. **Valid when the channel moves inside the window.** The exact version uses the correct taps per row. V7a: at the fastest rate (S = 1) the Monte-Carlo MSE of the oracle filter is within −0.32 % of the formula, and a filter fitted from samples matches the oracle within 0.11 % **[E]**. The quasi-static version would be 1.8 % off.
5. **Formulas** (`sweep_analyse`, 66–73):
   - J3 = mean e² over the window, per seed.
   - ε = (J3 − J_or)/J_or, the excess over the oracle.
   - ε_static = measured static-LMS excess, weighted by the trajectory.
   - ρ = (ε − ε_static)/(ε_plateau − ε_static): 0 means no tracking loss, 1 means no better than the best fixed filter for the averaged channel.
6. **Why the trajectory baseline exists.** LMS adds more noise on the harder part of the range: static excess at μ = 2⁻⁸ is 4.3 % at c = 40 and 11 % at c = 116 (F-5). A baseline measured only at the start would count that extra noise as tracking loss.
7. **Comparison with the literal baseline.**
   - The literal ε_static at c = 40 is 46.7 % at μ = 2⁻⁵ and 0.5 % at μ = 2⁻¹¹·⁵ (16 dB).
   - S*_MSE is **identical for μ ≤ 2⁻⁶·⁵** and differs by one grid step or becomes undefined for μ ≥ 2⁻⁶ (grid pilot log).
   - For BER the literal reference has zero errors, so it fails everywhere for large μ.
   - The literal values are still computed and reported (`blit`, lines 95–102).
8. **PPR-22's BER-relative-to-static criterion is still evaluated** (`bst` lines 87–94, trajectory reference; `blit` lines 95–102, literal reference) **[M]**.
9. **S*_BER, S*_MSE and S_cross are separate variables and outputs** (`res[...]['mse']`, `['ber']`, `S_cross_*`) **[M]**. The S_cross computation has the bug B-4.
10. **R3 loses accuracy but still beats R2: this is exactly the pilot picture.** ρ crosses 0.5 at S = 10–320 depending on μ, yet R3's BER stays far below R2's at every S. Meaning:
    - S*_MSE marks the loss of **accurate** tracking;
    - S*_BER marks the loss of **reliable** detection relative to the static case;
    - S_cross marks the loss of **usefulness** against the controls.

    Three different boundaries, all reported.
11. **Established against inconclusive (L1 pilot).**
    - **S*_MSE:** established for all 14 μ at both SNRs. It is bracketed, the seed half-width of ρ is ≤ 0.005, and the result is not sensitive to burst statistics.
    - **S*_BER:** established only for μ ≥ 2⁻⁵·⁵ (reference resolved). The rest is reference-limited or inconclusive, so the 12/14 dB study is needed.
    - **S_cross:** "not observed" for μ ≤ 2⁻⁵·⁵. For μ = 2⁻⁵ it lies between S = 5 and S = 2, pending the B-4 fix.

## B.5 P1–P3 scientific validation (your section 5)
1. **Same LMS loop for P1, P2 and P3 [M].** P1 calls `run_receivers`; P2, P3 and the sweep call `run_lms`; both end in `lms_receivers`.
2. **Why the mild channel is insufficient.**
   - Peak ISI a + 0.1 ≤ 0.70 < 1, so the eye never closes and R1 makes almost no noise-free errors.
   - ε_plateau = 0.60 / 0.98 (14 / 16 dB) is below the selection requirement of 1.0 (C1).
   - R2 makes fewer than 100 errors per 10⁷ bits at any S (C3b) **[E]**.
3. **Why the primary channel was selected.** It is the only channel meeting all of C1–C4 at both SNRs (F-6) **[E]**.
4. **The control is retained** in config ("mild": 26–77) and was used in P1 V4 and the P3 pilot. **It is not in the final sweep plan** (B-8).
5. **The 48 % mismatch.** The textbook formula assumes the best filter's error is white. On this ISI channel it is correlated (lag-1 coefficient −0.53), which adds the term −2ΣC(j) and gives 1.47× at first order **[M + E]** (`MISADJUSTMENT_DERIVATION.md`).
6. **Assumptions A1–A4** (small μ, stationarity, input independent of weight error at first order, fast decay of C(j)).
   - **Verified:** the exact C(j) by fourth-moment algebra matches the data; independent code agrees; shuffling removes the effect; the ISI sweep is tracked within 1.5–4 % **[E]**.
   - **Not verified:** a closed-form second-order term (1–6 % residual), and your review of the derivation (pending).
7. **1/μ recovery time.** Measured slopes −1.09, −0.98, −0.97 against model slopes −1.09, −1.02, −1.00 **[E]**. The model is mean-weight theory **[M under small-μ assumption]**.
8. **Noise bias in N_rec.** "Last time above the threshold" can only be pushed later by noise. On c = 116 the moving average is 3.61× noisier than i.i.d. A Monte Carlo of model plus noise reproduces all 12 values **[E]**.
9. **High MSE but small BER.** MSE averages the squared error. BER counts only errors that cross zero. After the mid jump, R2's output has a systematic residual (309 % above the oracle MSE), but the eye is still open, so few decisions flip (BER 7.5·10⁻⁶) **[E]**.
10. **μ_opt scaling is a hypothesis.** D-01: the square-root reference and a conditional 2/3 alternative, with the exponent measured. Preview 0.52 (16 dB) and 0.53 (14 dB); the interval is underestimated (B-5). **Not proven.**
11. **Results with weak samples or approximations.**
    - F-2 (one seed); V7b (one seed); P-07 convergence (one seed, superseded by F-4 and `check_NT`).
    - P3 pilot BER statistics (floor conflation); grid pilot BER (plain Wilson, 20 seeds).
    - The independence check (40 seeds; per-seed dispersion noisy).
    - The analytic ε_plateau (quasi-static); the exponent interval.

## B.6 FREEZE-1 audit (your section 6)
1. **μ float:** `MU_FLOAT = [2**-(5+0.5j) for j in 0..13]` = 2⁻⁵ … 2⁻¹¹·⁵, 14 values ✔ (`freeze_grids.py`).
2. **μ FPGA:** `MU_FPGA = [2**-k for k in 5..11]`, 7 values, all contained in MU_FLOAT ✔.
3. **S grid:** 5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1 (18 values) plus `None` (static) ✔ (`sweep.run_sweep` appends `None`, line 35).
4. **Whole periods:** `n_eval_for` (sweep 10–14) ✔. The occupancy check gives zero deviation from the quasi-static weights for every S **[E]**.
5. **Unequal window lengths.**
   - **No bias** in ε, ρ or BER expectation: every window contains whole periods, so each channel state has the same weight and the start (c_lo, going up) is the same for all S.
   - The lengths change only the **precision**, which is handled by using each point's own N_bits (`sweep_analyse`, line 69, `NB = ns * len(cw)`).
6. **11 static states and interpolation.** Static performance is measured at 11 states (c = 40, 48, …, 112, 116). The trajectory visits all 77 states. Interpolation fills the gaps; measuring all 77 would cost 7× more.
7. **Log interpolation.** Valid only for positive values; zeros fall back (B.3.11).
   - Evidence at 12 dB: log 0.96–1.02 against linear 0.90–0.97 relative to a direct slow-trajectory measurement **[E]**.
   - Not claimed to be the true between-state BER (A-1 condition).
   - At 14 and 16 dB, many states have zero errors, so linear interpolation with upper bounds applies and the point is labelled reference-limited.
8. **Linear interpolation is kept as a sensitivity column** — approved condition; **not yet implemented** (B-17).
9. **12 dB gives enough errors:** ≥ 297 expected reference errors for every μ **[E]**.
10. **Budget:**
    - Pilot timing projects 8–10 min per SNR for 100 seeds × 14 μ × 19 S plus statics.
    - The 14 dB 1500-seed study is about 1–2 h on both cores.
    - The control channel adds about 10 min per SNR.
    - All are projections **[A]**, to be confirmed on the first final point.
11. **Seed separation:**
    - pilot 1000–1099; final 2000–2099 (never used yet);
    - audit and check seeds 5000–5439 and 900000+; V2 seeds 7000+, 8000+, 17000+, 40000+, 60000+.
    - The proposed 6000–7499 overlaps V2 (B-9).
12. **Unresolved issues that could invalidate final results:**
    - B-1 and B-2 (BER intervals and reference uncertainty);
    - B-4 (S_cross);
    - B-8 (control channel);
    - B-15 (P2 down-step training);
    - B-17 (A-1 and A-4 not implemented);
    - B-5 (exponent interval wording).

    None of them concerns the LMS or the MSE results.

## B.7 FPGA feasibility (your section 7)
1. **Feasible on paper.**
   - XC7S50 resources: 120 DSP48E1 slices, about 2.7 Mbit of block RAM.
   - The parallel estimate is ≈ 51 DSP (43 %) per PPR-22 Table 3, plus about 3 multipliers not listed there: e² for the two MSE counters and the noise scaling σ·v. That gives **≈ 54 DSP (45 %)**.
   - This is an **estimate, not a synthesis result** **[A]**.
2. **How Table 3 was calculated:**
   - channel FIR, M = 3 → 3 multipliers;
   - R2 filter → L = 16;
   - R3 filter (16) + R3 update e·u_k (16) → 32;
   - μ is a power of two, so μ·(…) is a shift and costs nothing;
   - R1 is a comparator → 0.
3. **Presented as an estimate everywhere.** Recorded so in D-05 and the spec ✔.
4. **Update arithmetic per symbol:**
   - 1 subtraction (e = d − y);
   - 16 multiplications e·u_k;
   - 16 shifts (μ);
   - 16 additions into the coefficient accumulators.

   The filter needs 16 multiplications plus a 15-adder tree.
5. **Effect of precision on resources [A].**
   - One DSP48E1 multiplies 25 × 18 bits, so B_mul = 8, 12 or 16 bits costs one DSP per product either way. The **DSP count stays flat**.
   - B_acc (for example 26 bits) costs flip-flops (16 × B_acc per adaptive filter) and adder width. It could even sit inside the DSP's 48-bit accumulator register.
   - Wider adders lengthen carry chains and lower Fmax.
   - To be measured at L4.
6. **Main RTL risks:**
   - timing of multiply plus adder tree plus update at 100 MHz;
   - signed fixed-point saturation and rounding;
   - delay alignment (Δ, R1 offset);
   - correctness of the noise generator;
   - UART framing;
   - bit-exact agreement with L2.
7. **The time-multiplexed MAC is not implemented anywhere** (code search) ✔.
8. **No L1 result depends on the architecture** (A.11).
9. **What must be reproduced in L2 / RTL:**
   - static convergence to Wiener (V4a);
   - BER curves of R1/R2/R3 and S*_MSE / S*_BER at the 7 power-of-two μ;
   - N_rec at 2⁻⁷ … 2⁻¹⁰ (already powers of two);
   - the new item, underflow onset against B_acc.

   RTL must match L2 bit-exactly on exported vectors. The board must reproduce BER counts at a few presets above 10⁻⁴.
10. **Simplest path to a demonstration:**
    1. L2 bit-true model of exactly the RTL arithmetic (one B_mul and B_acc), including the LFSR noise.
    2. Export test vectors.
    3. RTL: channel + noise + R1/R2/R3 with an on-chip PRBS payload, so no UART payload yet.
    4. Bit-exact simulation against L2.
    5. Synthesis.
    6. Board: report only error counters over UART.
    7. Then add audio and image payloads.
    8. Then the word-length variants.

---

# C. PPR-22 compliance matrix

Categories:
- **Completed** — done as promised.
- **In progress** — planned and partly done.
- **Not started** — promised, nothing done yet.
- **Modified (justified)** — changed with a recorded reason, and the original intent is kept or the original is also reported.
- **Extension** — added, not promised.
- **CONTRADICTION** — what PPR-22 states is false or will not be done as written.

| PPR-22 section and exact wording (abridged) | Implemented | Evidence | Status | Contradiction? |
|---|---|---|---|---|
| 3.1 "identify the boundary in S beyond which the adaptive receiver ceases to outperform its controls" | S_cross | `sweep_analyse` 29–33, 103–104 | In progress (bug B-4) | No |
| 3.2 Obj. 1 reproducible profiles | Triangle + step, Δa = 2⁻⁷, seeded | `triangle_counter`, V0 | Completed (L1) | No |
| 3.2 Obj. 2 fixed-point LMS, Δ, training, precision | Δ and training done; fixed point not | V5, V6 | In progress | No |
| 3.2 Obj. 3 BER, MSE and N_rec vs rate for R1/R2/R3 | Pilot done; final pending | F-5, F-6, grid pilot | In progress | No |
| 3.2 Obj. 4 μ_opt exists, scales, survives fixed point | Float preview only | grid pilot | In progress | No |
| 3.2 Obj. 5 word length vs trackable rate and cost | — | — | Not started (final phase) | No |
| 4.1 "Nrec … return within a stated factor of its **pre-transition** steady-state value" | Post-transition level, sustained, κ = 0.25 | D-09, `n_rec_from` | Modified (justified: the pre-transition level can be unreachable); literal version recommended as sensitivity (B-13) | No |
| 4.2 a in [0.20, 0.60] "provisionally" | Control 0.203–0.602 kept; primary 0.31–0.91 added | config, F-6 | Modified (justified, provisional value) | No |
| 4.2 "The floating-point model will confirm that [triangle and sinusoid] give comparable tracking behaviour at matched average rates" | — | — | **Not started** | No (open promise) |
| Table 2 presets S1–S4 = 1000, 200, 50, 10, "provisional … fixed after floating-point simulation so that the set brackets the observed tracking boundary" | 18-value grid that brackets S* | FREEZE-1 | Completed as promised | No |
| 4.3 "Separate LFSRs with distinct primitive polynomials …"; validation by mean, variance, autocorrelation, saturation, reproducibility, BER effect | L1 Gaussian generator validated (V1, V2, V2c); LFSR generator not built | V1, V2, B-10 | Not started (hardware level) | No |
| 4.3 "measurements will accordingly be quoted only down to approximately 10⁻⁴" | Applies to the hardware generator; L1 labelled, dashed line | D-12 | Completed (as a labelling rule) | **No** (agreed) |
| 4.3 "Every comparison … uses identical transmitted data, identical channel trajectory and identical noise realisation. This is enforced by seeding" | Yes | A.4, V0 | Completed | No |
| 5.1 LMS equations (5)–(7), μ a power of two in hardware | Exact; power-of-two subset in the grid | A.3, `MU_FPGA` | Completed | No |
| 5.2 "grows roughly as μ tr(R)/2" | Measured 1.47× on this ISI channel; derivation found | F-1 | Extension (finding qualifies a cited approximation; PPR-22 itself says "roughly" and "exact constants depend on the … model") | No |
| 5.2 "μopt should scale as the square root of the variation rate. The step-size sweep … tests that scaling directly" | Square root tested; 2/3 added as an alternative | D-01 | Extension (test kept) | No |
| 5.3 "∆ will be selected by sweeping 0 ≤ ∆ ≤ L+M−2"; "whether the best ∆ remains constant as the channel varies" | Sweep done; stated rule; the best Δ varies (3–6) but the curve is flat | V5 | Completed | No |
| 5.3 "Because at least one channel preset is non-minimum phase — h = [0.5, 1.0] …" | No non-minimum-phase preset | B-14 | **Not started** | No (open promise) |
| 5.3 "The host will cross-correlate recovered against transmitted bits and report the peak lag" | Done in simulation (peaks at lag 2 and 0) | V3 | Completed (L1); hardware later | No |
| 5.4 "maximal-length LFSR sequence … giving R ≈ σ²I" | LFSR used ✔; but R = HHᵀ + σ²I | V6, D-10.3 | Completed, with a correction | **YES — factual error in PPR-22** |
| 5.4 "The polynomial and length will be reported" | x¹⁵ + x¹⁴ + 1, 30000 | config | Completed | No |
| 5.5 Three receivers; "conditions under which R2 matches or beats R3 (very slow variation …) will be reported rather than omitted" | R2 has lower MSE than R3 on the static control for every μ checked (5 of 14; e.g. 16 dB μ = 2⁻⁵: 0.01736 vs 0.01992); at S = 5000 R3 is already far better because the trajectory sweeps the full range | `audit_ber_deff_sensitivity_log.txt` | In progress (must be stated in the report) | No |
| 5.6 Three adaptation modes; "any reported result states which was used" | Supervised used and labelled; decision-directed coded but untested; pilot-assisted absent | A.6 | Partly completed; decision-directed **not started** | No |
| 5.7 S* "fastest preset at which R3 maintains a bit-error rate within a stated factor of its static-channel value" | S*_BER, f = 2; trajectory reference primary, literal also reported | `sweep_analyse` 87–102 | Modified (justified: "static-channel value" undefined in PPR-22; literal kept) | No |
| 5.7 "coefficient trajectories wk[n] compared against the known channel trajectory" | P2 done; continuous variation not yet | `fig_P2_coefficients.png` | In progress | No |
| 6.1 saturation, explicit widths | — | — | Not started (L2) | No |
| 6.2 Q1.24 extended accumulator; "the mismatch grows without bound" | Bounded trajectory, so the mismatch is bounded | D-10.5 | Correction | **YES — factual overstatement** |
| 6.3 D = 0 at about 10⁴ symbols/s | Unchanged; the target is a design choice below the 92 ksym/s UART ceiling | D-10.7 | Completed (no conflict) | No |
| 6.4 "synthesised at 8, 12 and 16 bits … DSP48E1, LUT, FF, Fmax, slack … BER, Nrec, S*" | Planned as B_mul / B_acc (D-04) | — | Not started (final) | No (extension of the design) |
| 6.5 Table 3, 51 DSP fully parallel | Parallel kept (D-05 reverted) | DECISIONS | Planned as written | No |
| 7.2 "Recorded audio is the primary mid-term demonstration" | Planned 24 Oct; synthetic placeholder unless a WAV is supplied | spec §9 | Not started | No (due 24 Oct) |
| 7.3 128 × 72 image, per-bit-plane metrics | — | — | Not started (final) | No |
| 9 "P1–P6 are software and constitute the mid-term target" | P6 (fixed-point model) deferred to the final phase | project decision | Not as written | **YES — schedule contradiction** |
| 10 "single fixed operating signal-to-noise ratio, chosen … so that the static-channel BER is low … a separate sweep establishes sensitivity" | 16 dB primary (static BER ≈ 0), 14 dB secondary; BER resolution at 12 and 14 dB | D-12, A-2 | Modified (justified: BER cannot be resolved at 16 dB; stated explicitly) | No |
| 10.1 about 12 noise levels, ≥ 10⁶ bits per point, vs theory | 12 points, 2·10⁶ bits, ≥ 100 errors, familywise criterion (+ V2c) | V2, P-11, B-10 | Completed (strengthened) | No |
| 10.2 Principal result BER vs S, R1/R2/R3 | Pilot done; final pending | grid pilot | In progress | No |
| 10.2 Step-size heatmap over (μ, S); reacquisition; trajectories; precision; payload | Heatmap data exists (pilot); others partly | — | In progress / not started | No |
| 10.2 "repeated across independent seeds and reported as averages … labelled with the validation level" | Yes | B.3.8 | Completed | No |
| 12.6 MathWorks behavioural cross-check of the Python model | — | — | Not started | No (open promise) |
| 13 Board demonstration with front-panel rate control | — | — | Not started (final) | No |
| 14 Success: "S* … shown to depend on μ and on coefficient word length … reacquisition time characterised" | μ dependence and N_rec at L1; word length later | F-5, grid pilot | In progress | No |
| 14 Prior 128×72 result (4,911 / 380 errors) | Configuration undocumented | spec §13 | Unverified | No (must be labelled) |
| 14/10 "R3 holding longer before also failing" (expectation that R3 fails at fast variation) | Yes in MSE (ρ → 1 for S ≤ 5) and in BER against the static reference; R3 still beats R2/R1 at S = 1 for μ ≤ 2⁻⁵·⁵ | F-6, grid pilot | Observed (L1 pilot) | No |
| 15 "No simulation output … in this or any subsequent report is AI-generated; all such results are produced and verified independently" | Simulations were written and run with AI assistance; revised wording drafted (D-06) | — | Must be rewritten | **YES — genuine contradiction (most important)** |

**Genuine contradictions: 4.**
1. Sec. 15 AI sentence.
2. Sec. 5.4 R ≈ σ²I.
3. Sec. 6.2 "grows without bound".
4. Sec. 9 midterm = P1–P6.

**Open promises (not contradictions yet):**
- triangle vs sinusoid comparison;
- non-minimum-phase preset;
- decision-directed mode;
- LFSR noise generator;
- MathWorks cross-check;
- the recorded-audio demonstration (P5);
- continuous coefficient trajectories;
- prior image result.

They become contradictions only if dropped without being stated.

**Revision note.** `PPR22_COMPARISON.md` (9 contradictions) counted justified methodological changes (channel range, N_rec definition, √ exponent, misadjustment constant, 10⁴ symbols/s) as contradictions. Under your stricter definitions they are not. I recommend replacing its classification with this matrix (decision E-7).

---

# D. Risk register (ranked)

| Rank | Risk | Impact: midterm | Impact: final | Impact: FPGA | Mitigation |
|---|---|---|---|---|---|
| 1 | AI-disclosure sentence false as written in PPR-22 | **High** (course policy) | High | — | Revised wording; team runs and reads the code before signing |
| 2 | BER intervals too narrow, reference uncertainty ignored (B-1, B-2) | Medium | Medium | Low | A-4 + paired seed bootstrap |
| 3 | 16 dB BER not resolvable (B-3) | Medium | Medium | Medium (hardware SNR) | 12/14 dB study (approved) |
| 4 | Midterm misses P6 and audio unless scheduled | Medium | — | — | State the P6 deferral; audio on 24 Oct |
| 5 | S_cross bug (B-4) | Medium (a headline wording) | Medium | — | Bug fix before the final analysis |
| 6 | Control channel absent from the final sweep (B-8) | Medium | Medium | — | Add it (about 10 min per SNR) |
| 7 | Final P2 down-step unconverged at μ = 2⁻¹⁰ (B-15) | Low–Medium | Medium | — | N_T = 60000 for that step, or report it |
| 8 | Exponent overclaimed (B-5) | Low–Medium | Medium | — | Sensitivity reporting |
| 9 | Bounded noise in hardware changes R1 BER strongly and R3 BER modestly (B-11) | Low | Medium | **High** (board BER ≥ 10⁻⁴ needs lower SNR) | FPGA noise model in L2; choose the hardware SNR then |
| 10 | Timing closure of the parallel datapath at 100 MHz | — | — | **High** | Multicycle within the symbol period (D = 0 kept), or a divided clock (PPR-22 Table 5) |
| 11 | Open PPR-22 promises (sinusoid, non-minimum phase, decision-directed, MathWorks) | Low | Medium | — | Do the cheap ones (non-minimum phase, sinusoid) or state them as future work |
| 12 | Unverified prior image result | Low | Low | — | Label it or reproduce it |

---

# E. Decision request — the smallest set that needs your approval before FREEZE-1

| # | Decision | Recommendation | Why it must be decided before FREEZE-1 |
|---|---|---|---|
| E-1 | **A-4:** burst-adjusted Wilson intervals for pass/fail (gap 20, sensitivity 10/40), plain Wilson kept as a sensitivity column, plus the **paired seed-level bootstrap** of BER_R3/BER_ref as a cross-check, so the reference uncertainty is included where both sides have ≥ 100 errors | Approve | Defines the BER statistics of the final analysis |
| E-2 | **Data-collection change** in `sweep.py`: also store the burst count per seed (no LMS change) | Approve | Bursts cannot be recovered after the run |
| E-3 | **Bug fix** of the S_cross computation (`sweep_analyse` lines 103–104, 113) to the PPR-22 definition | Approve | A headline quantity |
| E-4 | **Control channel** (26–77) included in the final sweep at 16 and 14 dB | Approve | D-03 commitment; must be in the frozen configuration |
| E-5 | **Seed range** for the 14 dB 1500-seed BER study: 100000–101499 instead of 6000–7499 | Approve | Seed sets are frozen |
| E-6 | **Final P2 down step:** N_T = 60000 for that step only, or keep 30000 and report R2 as not converged | N_T = 60000 for that step | The P2 configuration is frozen |
| E-7 | **Classification:** replace the earlier list with the compliance matrix of section C (4 genuine contradictions) and add the register rows | Approve | The item you put on hold |

**Can wait until after FREEZE-1** (none blocks the sweep): implementation of A-1 (approved), exponent sensitivity reporting, the non-minimum-phase P1 test, the triangle-vs-sinusoid check, the N_rec literal sensitivity, decision-directed mode, P6 timing, the image result.

**Audit files created (no existing file changed):**
- `code/audit/noise_model_check.py`;
- `code/audit/ber_deff_sensitivity.py`;
- `code/audit/gauss_tail_and_L_check.py`;
- `code/audit/execution_flow.dot`;
- the matching logs in `code/results/audit_*`;
- the figure `code/results/fig_audit_execution_flow.png`.

---
## Addendum (20 Oct, evening) — owner decisions and follow-up
- Decisions E-1 … E-7 recorded in `DECISIONS.md` (E-1, E-6, E-7 modified by the owner). Implementation and validation: `FREEZE_1_CHECKLIST.md` §4–5.
- **Risk register, rank 1 revised:** the AI-disclosure item is a low-priority wording fix. The course only asks for disclosure of where AI was used. Highest priorities are now the BER statistics (validated, §5 of the checklist) and the midterm scope (P5, P6a plan).
- **B-15 resolved:** a common N_T = 60000 for P2 passes all 16 convergence cases; 30000 fails for the "down" step at μ = 2⁻¹⁰.
- **B-1, B-2, B-4, B-5, B-8, B-9, B-17 addressed in code or configuration** (bootstrap primary with validation, S_cross fix, control channel, seeds, log interpolation, exponent variants).
- **Still open (not blocking FREEZE-1):** B-13 (literal N_rec sensitivity), B-14 (non-minimum-phase test), the triangle vs sinusoid check, decision-directed mode, MathWorks cross-check, image result.
