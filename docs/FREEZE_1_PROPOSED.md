# FREEZE-1 — final configuration proposed for confirmation (20 Oct 2026, after the validation checks)

**Status: PROPOSED. Nothing is frozen. The final sweep has NOT been started.** All numbers below are **L1 pilot** results (floating point; pilot seeds 1000–1019 or check seeds 5000+/5200+). Final seeds 2000–2099 are unused.

## 1. Result of the four validation checks

| Check | Outcome |
|---|---|
| **N_T = 30000 sufficient for every μ?** (`check_NT.py`, static c=40 training channel, 16 dB = slowest case, 40 seeds, against the Wiener filter) | **PASS.** Slowest mode: λ_min = 0.628 ⇒ time constant 1/(2μλ_min) = 2308 symbols at μ = 2⁻¹¹·⁵ (25 at 2⁻⁵). 30000 symbols = 13 time constants at the slowest μ. Mean-weight distance to the Wiener filter at N_T: 2.8·10⁻⁶ of ‖w_o‖² measured (1.0·10⁻⁶ predicted by the mean-weight model; difference is the noise floor of 40 seeds) → remaining excess MSE ≲ 2·10⁻⁴ J_min, against a steady-state excess of 0.4–47 %. At N_T/2 the distance is 9.9·10⁻⁴ (model value consistent), so the check can see an unconverged filter. **No change to N_T.** (The excess-MSE ratio last-5000-symbols / steady-state is 0.98–1.42; the 1.42 at μ = 2⁻¹¹·⁵ is within the sampling noise of a 0.4 % quantity and is not used.) |
| **Window rule: exact lengths, weighting, uncertainty, budget** (`check_windows.py`) | **PASS with caveats.** Weighting: counter occupancy over a whole number of triangle periods equals the quasi-static weights (interior 1/76, ends 1/152) with maximum deviation 0 for all 18 S. Lengths (symbols, P periods): S=5000 760000 (P=1, +400 %), 2000 304000 (P=1, +100 %), 1000 and 500 152000, 320 145920 (−4 %), **224 136192 (−10.4 %, P=4)**, 160 145920, 112 153216, 80 145920, 56 153216, 40/20/10/5/2/1 152000, 28 153216, 14 151088. Slow S need the longer windows (one period minimum). Seed uncertainty (95 % half-width of mean ρ near ρ = 0.5, 20-seed pilot; ×0.45 for 100 seeds): 0.001–0.005 at 100 seeds, ≤0.0016 at S = 5000. So S* is set by the grid spacing, not by seed noise; the statistical uncertainty is not the limiting factor. |
| **Budget** | **My earlier "≈2 h per SNR" was wrong.** Measured pilot rate ≈ 1.7·10⁷ symbols/s (all 14 μ, 20 seeds, per S: 2–7 s; S = 5000: 16 s). Projected final sweep, 100 seeds: about 8–10 min per SNR including the 11 static baselines. This is a projection from the pilot timing (other jobs were running), to be confirmed on the first final point. |
| **12 dB static BER measurable?** (`ber_static_grid.py`, `ber_static_analyse.py`; 100 seeds × 152000 bits per c, 11 c, 14 μ) | **PASS at 12 dB, FAIL at 16 dB, PARTIAL at 14 dB.** Expected reference errors in a final window (100 seeds × 152000 bits): 12 dB ≥ 297 for every μ (resolved criterion ≥ 100); 14 dB: resolved for μ ≥ 2⁻⁶·⁵ (124) only, 52 at 2⁻⁷ and 8–27 for 2⁻⁷·⁵ … 2⁻¹¹·⁵ (S=5000, one period: 264 at 2⁻⁷, 136 at 2⁻⁷·⁵, then 40–88); 16 dB: resolved for μ ≥ 2⁻⁵·⁵ (239) only; from 2⁻⁷ the static BER is ≤ 6·10⁻⁸ (all c nodes but the hardest have zero errors in 1.5·10⁷ bits) and 100 reference errors would need 1.8·10⁹ bits (2⁻⁷) to 5.8·10¹⁰ bits (2⁻⁹·⁵…2⁻¹¹), at 2⁻¹¹·⁵ not a single static error was seen at any c. Lowering the SNR therefore works (12 dB) but is not automatic: 14 dB is only partly sufficient. |
| **BER baseline accuracy** (new, `ber_baseline_check.py`, 12 dB) | **AMENDMENT NEEDED.** The static BER changes by up to four orders of magnitude over the c range (e.g. μ=2⁻⁵: 7.8·10⁻⁶ at c=40, 2.8·10⁻² at c=116), so linear interpolation between the 8-step nodes over-estimates the reference by 4–8 %. Independent test: R3 measured on the slowest trajectory (S = 5000, 40 seeds, 5200–5239) agrees with the linear-interpolated reference to 0.90–0.97 and with the log-linear interpolated reference to 0.96–1.02 for all 14 μ. The effect (≤ 8 %) is small against f = 2 but it is a bias in the favourable direction. **Proposed amendment A-1: BER_ref uses log-linear interpolation whenever all 11 static nodes have ≥ 1 error; otherwise the linear/upper-bound convention of P-10 applies; the linear value is always reported next to it.** |

## 2. Configuration proposed for confirmation

**Fixed (approved):** channel [1, a[n], 0.1], c 40→116, L = 16, Δ = 2, supervised standard LMS, three receivers on identical data; N_T = 30000 (check passed); 16 dB primary tracking / MSE, 14 dB secondary; ρ_th = 0.5 (bands 0.25, 0.75), f = 2 (bands 1.5, 5); P-10, P-11, P-12 as in DECISIONS.md; BER and MSE separate headline results.

**Grids (approved, P-13):** μ_float = 2^−5, 2^−5.5, …, 2^−11.5 (14); μ_FPGA = 2^−5 … 2^−11 (7); S = 5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1 plus static; static baseline nodes c = 40, 48, …, 112, 116. Window rule N_eval = P·152·S (whole triangle periods, P = max(1, round(152000/(152 S)))) — exact lengths in §1.

**Final tracking sweep:** 16 dB and 14 dB, 100 seeds 2000–2099, static baselines 100 seeds, all 14 μ × 18 S. MSE/ρ: S*_MSE, ρ bands, μ_opt(S) and exponent fit (bracketed, ρ ≤ 0.75 only). BER at 16 dB is reported with the P-10 labels (resolved/reference-limited; conditional passes 'p'); fails are rigorous; S*_BER only where demonstrated monotonic.

**BER-resolution study (Option A), proposed design — needs confirmation:**
- **12 dB:** standard configuration (100 seeds 2000–2099, 100-seed statics): reference resolved for all 14 μ (≥ 297 expected errors). Full μ and S grids.
- **14 dB:** the standard run resolves μ ≥ 2⁻⁶·⁵ only. For μ ≤ 2⁻⁷ a separate BER-only run with **1500 seeds** (6000–7499; ≈ 2.3·10⁸ bits per point, ≥ 120 expected reference errors for every μ at the 152000-symbol windows) and statics with the same 1500 seeds on the 11 nodes. Projected cost from the measured rate ≈ 1–2 h on both cores (projection only).
- **16 dB:** not resolvable for small μ (up to 5.8·10¹⁰ bits per point); remains reference-limited and is reported as such; this is not hidden.
- Amendment A-1 (log-linear BER baseline interpolation) applied in all of the above.

## 3. Amendments to PPR-22 / earlier statements (for confirmation)
- A-1 as above. 
- A-2 BER-resolution plan above (12 dB new secondary BER operating point; 14 dB with 1500 seeds).
- A-3 Correction of my earlier budget estimate (≈ 8–10 min per SNR, not 2 h) and therefore of option C: raising the 16 dB record length is cheap for μ ≥ 2⁻⁶ but still infeasible for μ ≤ 2⁻⁹ (hours per point), so Option A stands.
- No change to the LMS algorithm, the receivers or the research question.

## 4. What I need from you
Confirm (or edit) §2 and the amendments A-1 … A-3. Until then the final sweep is not started.

## 5. Status of the confirmations (20 Oct, later)
- Window rule, A-3 (run-time correction): **approved**. A-2 (BER study design): **approved**. A-1 (log-linear BER interpolation): **approved conditionally** (linear kept as sensitivity; log interpolation not claimed to be the true BER).
- New from the independence check required by the A-2 approval: errors occur in short bursts, so **A-4 (burst-adjusted BER intervals)** is proposed (DECISIONS.md). It is not yet approved, so FREEZE-1 is not complete and the final sweep has not started.
- On hold: classification of contradictions/extensions/gaps.
