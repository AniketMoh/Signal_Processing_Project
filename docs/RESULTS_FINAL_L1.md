# Final results — P4 (tracking sweep), P2 (abrupt transitions), P6a status, P5 status (20 Oct 2026)

**Levels.** Every number in sections 1–5 is **L1** (floating-point simulation, ideal Gaussian noise, supervised LMS). Section 6 refers to **L2** (bit-true fixed point, `P6A_REPORT.md`). **No result in this document is a hardware (L3–L5) result**, and none is presented as hardware validation.

**Configuration.** FREEZE-1 as approved on 20 Oct.
- **Primary channel** 40–116 (a 0.31–0.91); **control channel** 26–77 (a 0.20–0.60).
- **Step sizes:** 14 μ values, 2⁻⁵ … 2⁻¹¹·⁵.
- **Variation rates:** 18 S values, 5000 … 1, plus the static case.
- **Seeds:** 100 final seeds (2000–2099); the 14 dB BER study used 1500 seeds (100000–101499) for μ ≤ 2⁻⁷.
- **Training:** N_T = 30000 for the continuous sweep, 60000 for P2.
- **Statistics:** paired seed-level bootstrap as the primary BER evidence, reference resolution judged by observed errors, Wilson variants as sensitivities.
- **No frozen parameter was changed.** Corrections made during analysis are logged in §7 and in `DECISIONS.md`.

**Figures** (`code/results/final/`):
- `fig_boundaries_vs_mu.png`;
- `fig_ber_vs_S_primary_{16,14,12}.png` (with the dashed 10⁻⁴ hardware-noise line);
- `fig_rho_vs_S_{primary,control}_{16,14}.png`;
- `fig_mu_opt_primary_{16,14}.png`;
- `fig_eps_heatmap_primary_{16,14}.png`;
- P2: `code/results/final_{16,14}dB_fig_P2_*.png`.

**Full per-point output:** `code/results/final/analysis_*_log.txt` and `.json`. The tables below are generated from those files by `final_tables.py`, not typed by hand.

## 1. Headline findings
1. **MSE tracking boundary (S*_MSE) is located for every μ.**
   - It is bracketed inside the grid in all 68 (μ, run) cases where ρ is defined. No pass ever follows a non-pass; in 65 of the 68 every point after the first non-pass is a rigorous fail, and the other 3 contain an inconclusive point.
   - It moves to slower variation as μ falls: 16 dB gives 14, 10, 10, 14, 20, 20, 28, 40, 56, 80, 112, 160, 224, 320 for μ = 2⁻⁵ … 2⁻¹¹·⁵.
   - For μ ≤ 2⁻⁷·⁵ the boundary is the same at 12, 14 and 16 dB and on both channels, to within one grid step. At this resolution it is set by μ (the adaptation time constant), not by noise level or channel.
2. **BER tracking boundary (S*_BER, PPR-22's criterion) is resolved at 12 and 14 dB for most μ.**
   - It lies 1–3 grid steps at **slower** variation than S*_MSE. Example, μ = 2⁻⁸: S*_MSE = 28, S*_BER = 56 (12 dB) and 112 (14 dB).
   - The BER criterion is stricter, and stricter at higher SNR, because the static reference BER is smaller.
   - At 16 dB the BER reference is measurable only for μ ≥ 2⁻⁵·⁵. There, S*_BER = 5 and 10.
3. **S_cross: on the primary channel R3 never stops outperforming both controls for μ ≤ 2⁻⁵·⁵.** The result is "no S_cross observed within the grid".
   - For μ = 2⁻⁵ a **loss of advantage is confirmed** at S = 2 (12, 14 and 16 dB).
   - So R3 can lose tracking **accuracy** (ρ > 0.5) long before it stops being **useful** compared with R1 and R2.
4. **Optimum step size grows with the variation rate.**
   - Primary channel slope 0.52 (16 dB), 0.53 (14 dB), 0.51 (12 dB), with systematic bands 0.48–0.55. This is consistent with PPR-22's square-root prediction.
   - The control channel gives 0.59 / 0.58 (bands 0.55–0.61), consistent with neither ½ nor ⅔.
   - The exponent is therefore **channel-dependent**, and the local slope changes along the S range (visible curvature in `fig_mu_opt_*`). Square-root scaling is a good description on the primary channel only.
5. **Abrupt transitions (P2, final).** Recovery time is proportional to 1/μ: log–log slopes −1.08 / −1.00 / −0.99 (16 dB) and −1.13 / −0.99 / −0.98 (14 dB), against the mean-weight model −1.07…−1.00.
6. **Finite precision (P6a, L2): no measurable effect on the tracking boundary** within the approved word lengths with round-to-nearest. Truncation does cost accuracy (section 6).

## 2. Tables
### Table 1 — S*_MSE (ρ_th = 0.5; bands ρ_th 0.25 / 0.75; literal-baseline sensitivity)

| μ | primary 16 dB | primary 14 dB | primary 12 dB | control 16 dB | control 14 dB |
|---|---|---|---|---|---|
| 2^-5 | **14** (20/10; lit None) | ρ undefined* | ρ undefined* | **10** (14/10; lit 14) | **56** (80/40; lit None) |
| 2^-5.5 | **10** (20/10; lit 14) | **14** (20/10; lit 28) | **28** (40/28; lit None) | **10** (14/10; lit 10) | **10** (20/10; lit 20) |
| 2^-6 | **10** (20/10; lit 14) | **14** (20/10; lit 14) | **14** (28/10; lit 28) | **10** (14/10; lit 10) | **10** (20/10; lit 14) |
| 2^-6.5 | **14** (28/10; lit 14) | **14** (28/10; lit 14) | **14** (28/10; lit 20) | **14** (20/10; lit 14) | **14** (20/10; lit 14) |
| 2^-7 | **20** (28/10; lit 20) | **20** (28/10; lit 20) | **20** (28/10; lit 20) | **14** (28/10; lit 14) | **20** (28/10; lit 20) |
| 2^-7.5 | **20** (40/10; lit 20) | **20** (40/10; lit 20) | **20** (40/14; lit 28) | **20** (40/14; lit 20) | **20** (40/14; lit 20) |
| 2^-8 | **28** (56/14; lit 28) | **28** (56/14; lit 28) | **28** (56/14; lit 28) | **28** (56/14; lit 28) | **28** (56/20; lit 28) |
| 2^-8.5 | **40** (80/20; lit 40) | **40** (80/20; lit 40) | **40** (80/20; lit 40) | **40** (80/20; lit 40) | **40** (80/20; lit 40) |
| 2^-9 | **56** (112/28; lit 56) | **56** (112/28; lit 56) | **56** (112/28; lit 56) | **56** (112/28; lit 56) | **56** (112/28; lit 56) |
| 2^-9.5 | **80** (160/40; lit 80) | **80** (160/40; lit 80) | **80** (160/40; lit 80) | **80** (160/40; lit 80) | **80** (160/40; lit 80) |
| 2^-10 | **112** (224/56; lit 112) | **112** (224/40; lit 112) | **112** (224/40; lit 112) | **112** (224/56; lit 112) | **112** (224/56; lit 112) |
| 2^-10.5 | **160** (320/80; lit 160) | **160** (320/56; lit 160) | **160** (320/56; lit 160) | **160** (320/80; lit 160) | **160** (320/80; lit 160) |
| 2^-11 | **224** (500/112; lit 224) | **224** (500/80; lit 224) | **160** (500/80; lit 160) | **224** (500/112; lit 224) | **224** (500/112; lit 224) |
| 2^-11.5 | **320** (1000/160; lit 320) | **320** (500/112; lit 320) | **224** (500/112; lit 320) | **320** (500/160; lit 320) | **320** (500/160; lit 320) |

*ρ undefined: the static LMS excess already exceeds the plateau (ε_static ≥ ε_plateau), so the tracking-loss scale has no room.

### Table 2 — S*_BER (f = 2; primary method = paired seed bootstrap; R = resolved, C = conditional; [a, b] = transition bracket when the boundary point itself is inconclusive, S*_BER not demonstrated under the strict rule)

| μ | 12 dB (100 seeds) | 14 dB (100 seeds, or 1500 seeds for μ ≤ 2^-7) | 16 dB (100 seeds) | f = 1.5 / 5 at 12 dB |
|---|---|---|---|---|
| 2^-5 | **2** (R) | **5** (R) | **5** (R) | 5 / None |
| 2^-5.5 | **5** (R) | **10** (R) | **10** (R) | 10 / None |
| 2^-6 | **10** (R) | **14** (R) | **20** (C) | 14 / 5 |
| 2^-6.5 | **14** (R) | n.d. [28, 14] | n.d. [80, 14] (C) | None / 5 |
| 2^-7 | n.d. [28, 14] | **40** (R) | n.d. (reference-limited) | 40 / 10 |
| 2^-7.5 | **40** (R) | **80** (R) | n.d. (reference-limited) | None / 14 |
| 2^-8 | **56** (R) | **112** (R) | n.d. [56, 28] (C) | 80 / 20 |
| 2^-8.5 | **80** (R) | **160** (R) | n.d. (reference-limited) | None / None |
| 2^-9 | **112** (R) | n.d. [320, 160] | n.d. (reference-limited) | None / None |
| 2^-9.5 | n.d. [224, 112] | n.d. [500, 224] | n.d. [320, 56] (C) | None / None |
| 2^-10 | n.d. [320, 160] | n.d. [1000, 320] | n.d. (reference-limited) | None / None |
| 2^-10.5 | n.d. [500, 224] | **1000** (R) | n.d. [320, 160] (C) | None / 160 |
| 2^-11 | **500** (R) | n.d. [2000, 500] | n.d. [500, 160] (C) | 1000 / 224 |
| 2^-11.5 | n.d. [1000, 320] | n.d. [2000, 500] | n.d. [500, 224] (C) | 1000 / 320 |

### Table 3 — BER status strings (S from 5000 on the left to 1 on the right; P/F/? = resolved pass/fail/inconclusive, p = conditional pass)

| μ | 12 dB | 14 dB | 16 dB | control 14 dB |
|---|---|---|---|---|
| 2^-5 | `PPPPPPPPPPPPPPPPPF` | `PPPPPPPPPPPPPPPPFF` | `PPPPPPPPPPPPPPPPFF` | `ppppppppppppppppFF` |
| 2^-5.5 | `PPPPPPPPPPPPPPPPFF` | `PPPPPPPPPPPPPPPFFF` | `PPPPPPPPPPPPPPPFFF` | `pp??p?p??p??????FF` |
| 2^-6 | `PPPPPPPPPPPPPPPFFF` | `PPPPPPPPPPPPPPFFFF` | `pppppppppppppFFFFF` | `pp?ppppppp??ppp?FF` |
| 2^-6.5 | `PPPPPPPPPPPPPPFFFF` | `PPPPPPPPPPPP?FFFFF` | `ppppppppp????FFFFF` | `ppppppppppppppp???` |
| 2^-7 | `PPPPPPPPPPPP?FFFFF` | `PPPPPPPPPPPFFFFFFF` | `ppppp?ppp???FFFFFF` | `ppppppppppppppp???` |
| 2^-7.5 | `PPPPPPPPPPPFFFFFFF` | `PPPPPPPPPFFFFFFFFF` | `ppppp?ppp???FFFFFF` | `ppppppppppppppp?p?` |
| 2^-8 | `PPPPPPPPPPFFFFFFFF` | `PPPPPPPPFFFFFFFFFF` | `pppppppppp?FFFFFFF` | `ppppppppppppppppp?` |
| 2^-8.5 | `PPPPPPPPPFFFFFFFFF` | `PPPPPPPFFFFFFFFFFF` | `pppppp?p??FFFFFFFF` | `ppppppppppppppppp?` |
| 2^-9 | `PPPPPPPPFFFFFFFFFF` | `PPPPP?FFFFFFFFFFFF` | `ppppp??p??FFFFFFFF` | `ppppppppppppppppp?` |
| 2^-9.5 | `PPPPPP?FFFFFFFFFFF` | `PPPP?FFFFFFFFFFFFF` | `ppppp????FFFFFFFFF` | `ppppppppppppppppp?` |
| 2^-10 | `PPPPP?FFFFFFFFFFFF` | `PPP?FFFFFFFFFFFFFF` | `ppppp??F?FFFFFFFFF` | `ppppppppppppppppp?` |
| 2^-10.5 | `PPPP?FFFFFFFFFFFFF` | `PPPFFFFFFFFFFFFFFF` | `ppppp?FFFFFFFFFFFF` | `ppppppppppppppppp?` |
| 2^-11 | `PPPPFFFFFFFFFFFFFF` | `PP?FFFFFFFFFFFFFFF` | `pppp??FFFFFFFFFFFF` | `ppppppppppppppppp?` |
| 2^-11.5 | `PPP?FFFFFFFFFFFFFF` | `PP?FFFFFFFFFFFFFFF` | `pppp?FFFFFFFFFFFFF` | `ppppppppppp?ppppp?` |

### Table 4 — S_cross (paired bootstrap of BER_R3 − min(BER_R1, BER_R2); A = advantage demonstrated, L = loss confirmed, ? = inconclusive)

| run | μ with any non-A point | result |
|---|---|---|
| primary_16 | 2 of 14 | 2^-5: advantage demonstrated down to S = 5; first S without it = 2 (confirmed loss of advantage); 2^-5.5: advantage demonstrated down to S = 2; first S without it = 1 (inconclusive (advantage no longer demonstrated)) |
| primary_14 | 1 of 14 | 2^-5: advantage demonstrated down to S = 5; first S without it = 2 (confirmed loss of advantage) |
| primary_12 | 1 of 14 | 2^-5: advantage demonstrated down to S = 5; first S without it = 2 (confirmed loss of advantage) |
| primary_14_ber14 | none | no S_cross observed within the grid for any μ |
| control_16 | 14 of 14 | 2^-5: advantage demonstrated down to S = 56; first S without it = 40 (inconclusive (advantage no longer demonstrated)); 2^-5.5: advantage demonstrated down to S = 2000; first S without it = 1000 (inconclusive (advantage no longer demonstrated)); 2^-6: advantage demonstrated down to S = 2000; first S without it = 1000 (inconclusive (advantage no longer demonstrated)); 2^-6.5: advantage demonstrated down to S = 5000; first S without it = 2000 (inconclusive (advantage no longer demonstrated)); … (14 μ values in total) |
| control_14 | 1 of 14 | 2^-5: advantage demonstrated down to S = 2; first S without it = 1 (confirmed loss of advantage) |

### Table 5 — optimum step size exponent d log2 μ_opt / d log2(1/S)

| run | baseline fit | systematic band (7 variants) | statistical 95 % (seed bootstrap) | points |
|---|---|---|---|---|
| primary_16 | 0.519 | 0.487 – 0.543 | 0.5187 – 0.5193 | 15 |
| primary_14 | 0.525 | 0.493 – 0.550 | 0.5250 – 0.5257 | 15 |
| primary_12 | 0.511 | 0.476 – 0.542 | 0.5103 – 0.5110 | 14 |
| control_16 | 0.593 | 0.570 – 0.610 | 0.5932 – 0.5937 | 15 |
| control_14 | 0.575 | 0.551 – 0.596 | 0.5744 – 0.5749 | 14 |

## 3. P2 final (abrupt transition, N_T = 60000, 100 final seeds)

| Step | Eb/N0 | N_rec (κ = 0.25) for μ = 2⁻⁷ / 2⁻⁸ / 2⁻⁹ / 2⁻¹⁰, measured | Model (noise-free) | Slope measured / model |
|---|---|---|---|---|
| large_up 40→116 | 16 dB | 1687 / 3403 / 7875 / 15319 | 1376 / 3062 / 6363 / 12923 | −1.08 / −1.07 |
| mid_up 40→77 | 16 dB | 434 / 928 / 1694 / 3612 | 398 / 821 / 1660 / 3334 | −1.00 / −1.02 |
| down 116→40 | 16 dB | 583 / 1095 / 2220 / 4531 | 543 / 1085 / 2166 / 4326 | −0.99 / −1.00 |
| large_up | 14 dB | 977 / 2660 / 5347 / 10598 | 886 / 2030 / 4260 / 8684 | −1.13 / −1.09 |
| mid_up | 14 dB | 341 / 653 / 1228 / 2736 | 300 / 622 / 1259 / 2529 | −0.99 / −1.02 |
| down | 14 dB | 508 / 979 / 1961 / 3859 | 475 / 948 / 1892 / 3779 | −0.98 / −1.00 |

- **R2 after the large jump** matches the analytic frozen-filter MSE within 0.1–1.1 %. Example, 16 dB: 0.3963 measured against 0.3932 analytic at μ = 2⁻⁷.
- **BER at μ = 2⁻⁸, 16 dB, large_up, first 2000 symbols after the jump:** R1 0.142, R2 8.4·10⁻³, R3 6.8·10⁻⁴. Over the last 20000 symbols R3 makes 0 errors.
- **Measured N_rec is above the noise-free model on the harsh channel** (up to about 25 %, with wide upper intervals, e.g. [1607, 14837]). This is the known one-sided bias of a "last crossing" statistic (F-5), not a model failure.
- **New observation (logged):** R2's MSE after the "down" step is 0.7–2.7 % **below** the analytic value for the ideal trained filter.
  - Diagnostic `audit/p2_down_frozen_check.py`: the measurement equals the analytic MSE of the **actual** frozen weights to within +0.03 %, so the difference lies in the weights.
  - At μ = 2⁻¹⁰ the mean-weight model predicts exactly this offset: −2.10 % predicted, −2.3 % measured. The slowest mode of the harsh channel (λ_min = 0.07) still holds 1 % of its weight error after 60000 symbols.
  - The MSE check used for E-6 measured MSE on the **training** channel, where this residual is invisible (quadratic). On the other channel it acts linearly.
  - With 120000 symbols the model residual falls to 0.03 %.
  - At μ = 2⁻⁷ the offset is mostly common to all seeds. With seed-dependent random training it drops to −0.5 % (not significant), so it is linked to the shared PRBS training segment.
  - **No result was changed. A decision is requested in §7.**

## 4. Statistically inconclusive or limited findings (reported, not hidden)
- **Transition point inconclusive.** For several μ the grid point at the BER transition is inconclusive ('?') while every faster point fails. Examples: 12 dB μ = 2⁻⁷, 2⁻⁹·⁵, 2⁻¹⁰, 2⁻¹⁰·⁵, 2⁻¹¹·⁵; 14 dB μ = 2⁻⁶·⁵, 2⁻⁹, 2⁻⁹·⁵, 2⁻¹⁰, 2⁻¹¹, 2⁻¹¹·⁵. Under the frozen strict rule S*_BER is then **not demonstrated**; the bracket is reported instead (Table 2).
- **16 dB BER is reference-limited for μ ≤ 2⁻⁶.** Passes are conditional ('p'); fails remain rigorous.
- **Control channel BER.** All passes are conditional at 14 and 16 dB: errors are too rare to resolve the reference, as expected for the mild channel. At 16 dB the control-channel S_cross is mostly inconclusive because R1, R2 and R3 all make almost no errors.
- **ρ undefined for μ = 2⁻⁵ at 12 and 14 dB.** The static excess of LMS already exceeds the plateau, so no MSE boundary is defined there.
- **Exponent.** The seed-only interval (±0.0005) is not the real uncertainty. The systematic band (±0.03) is.
- **N_rec upper intervals are wide on the harsh channel** (last-crossing statistic).

## 5. Plain-language explanation (for the viva)
- **Why R1 and R2 have flat BER curves.** Both never adapt. Every window covers whole up-and-down periods, so they see the same mix of channel states whatever the speed. Only how fast the states pass changes, and a receiver that never adapts cannot notice speed. R3 is the only receiver whose error depends on the speed, which is exactly what the experiment isolates.
- **Why a smaller μ fails at slower variation.** μ sets how quickly the filter can move, with a time constant of about 1/(μλ). Halving μ doubles the time the filter needs to follow a change, so the channel must change about half as fast for the filter to keep up. That is why S*_MSE roughly doubles (one to two grid steps) for each halving of μ.
- **Why the BER boundary sits at slower variation than the MSE boundary.** The BER test compares R3 with its own static BER. At high SNR that BER is tiny, so even a small extra error from lag doubles it. The MSE test asks for half of the possible loss, which is a looser requirement.
- **Why R3 still beats R2 when tracking is "lost".** "Lost" here means R3 is no longer near the best possible filter. It still follows the channel roughly, while R2 does not follow it at all. Usefulness (S_cross) and accuracy (S*) are different questions with different answers.
- **Optimum step size.** Large μ reacts quickly but jitters; small μ is smooth but lags. The best μ balances the two. A faster channel needs a larger μ, roughly in proportion to the square root of the speed on our primary channel. This is a measured trend with a stated uncertainty band, not a law.
- **What "inconclusive" means.** The data at that point cannot tell pass from fail with 95 % confidence. It is honest to report it as such rather than to round it either way.

## 6. P6a (L2) — summary (details in `P6A_REPORT.md`)
- **T1:** wide words reproduce L1 exactly (0 decision differences in 3.8·10⁶ decisions).
- **T2:** an 8-bit multiplier word costs 2–9 % MSE; 12 and 16 bits ≤ 0.2 %.
- **T3:** stall fractions match the prediction. Round to nearest is robust (+0.33 % MSE at 47 % stalls); truncation biases (+31 % at μ = 2⁻¹¹, 16-bit accumulator).
- **T4/T4b:** S*_MSE identical to L1 for every tested width.
- **T5:** the LFSR noise generator matches the exact Irwin–Hall BER prediction.
- **T6:** RTL reference vectors exported.
- **T7:** N_rec unchanged except through the 8-bit static reference level.
- **Scope:** P6a covers the P6 software commitments of PPR-22, except the full word-length × μ × S study (done for selected μ) and the hardware cost part (P9).

## 7. Corrections logged and decisions needed
**Logged corrections and additions during analysis** (no frozen parameter changed; all in `DECISIONS.md`):
- reference resolution uses observed counts (owner rule);
- S*_BER labelled resolved or conditional;
- ρ marked undefined when ε_static ≥ ε_plateau (previously this produced a misleading "no failure");
- a descriptive transition bracket where S*_BER is not demonstrated;
- the P6a T7 first attempt with 20 seeds rejected as noise-dominated and rerun with 100 seeds;
- an L2 coefficient-history timing alignment (recording after the update, as in L1).

**Decisions for you:**
1. **P2 "down" step R2 offset (§3).** Either (a) keep N_T = 60000 and report the offset with its explanation, or (b) rerun all P2 with N_T = 120000 (about 15 minutes; a change to a frozen value). **I recommend (b)**, because E-6 asked for adequately converged filters and the weight-space residual is 1 % at μ = 2⁻¹⁰.
2. **Inconclusive transition points.** Keep the strict rule and report brackets (recommended for the midterm), or approve a refined rule for the final report: P…P, then at most one '?', then F…F counts as monotonic, with S* = the last P, labelled as such.
3. **P6 extension (optional).** To locate where precision starts to limit tracking, extend L2 to B_acc ∈ {10, 12, 14} and truncation at μ ∈ {2⁻⁸, 2⁻¹⁰}. This is outside the approved grid.
4. **P5:** please send your voice recording. The pipeline is ready and tested only with a temporary debug tone, which is not presented as a result.
