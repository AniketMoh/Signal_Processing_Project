# P6a — fixed-point software model (level L2): results and scope (20 Oct 2026)

**Level L2 = bit-true fixed-point simulation in Python.** Nothing here is an RTL, synthesis or board result (L3–L5). The LMS equations are identical to L1; only the arithmetic is finite precision. Code: `code/fxp_lib.py` (model), `code/p6a_tests.py` (tests T1–T7). Outputs: `code/results/p6a/`.

## 1. Arithmetic (approved defaults; dynamic range checked)
| Signal | Format | Rule |
|---|---|---|
| received sample r, delay line u | s16.12 (±8) | round to nearest from channel + noise, saturate |
| desired symbol d | s16.12 | ±1 exact |
| coefficient accumulator | s(B_acc).(B_acc−2), B_acc ∈ {16, 26, 32} | updates added here, saturate |
| multiplier coefficient | s(B_mul).(B_mul−2), B_mul ∈ {8, 12, 16} | B_mul MSBs of the accumulator, round to nearest, saturate |
| products w·u, adder tree | B_mul+16 and B_mul+20 bits | exact (no rounding) |
| y, e = d − y | s16.12 | y rounded to nearest; saturate |
| update μ·e·u, μ = 2⁻ᵖ | e·u exact (32 bits), shift by p | rounded to the accumulator LSB (nearest; truncation as sensitivity) |

**Baseline:** B_mul = 12, B_acc = 26.

**Dynamic-range check:**
- |w| ≤ 1.10 in every LMS run (jumps, S = 1, μ up to 2⁻⁵); the Wiener filter has |w| ≤ 0.987.
- |r| ≤ 2.73 and |y|, |e| ≤ 3.73.
- The ±2 and ±8 ranges therefore leave headroom. No saturation is expected in normal operation.

## 2. Results

**T1 — equivalence (very wide words B_mul = 24, B_acc = 48).**
- |J_L2 − J_L1| ≤ 2.3·10⁻⁷ in all six cases (criterion 10⁻⁶).
- 0 decision differences in 3.8·10⁶ decisions.
- Coefficient difference ≤ 4.6·10⁻⁵. **PASS**: the L2 model implements the same LMS as L1.

**T2 — static steady-state MSE, L2 relative to L1** (14 dB, 6 seeds):

| (B_mul, B_acc) | c = 40 | c = 116 |
|---|---|---|
| (8, any) | +1.7 … +2.5 % | +0.8 % (μ = 2⁻⁵) … +8.9 % (μ = 2⁻¹⁰) |
| (12, 16) | ≤ 0.03 % | ≤ 0.21 % (largest at μ = 2⁻¹¹) |
| (12, 26) baseline, (12, 32), (16, ·) | ≤ 0.02 % | ≤ 0.02 % (0.20 % at (16, 16), μ = 2⁻¹¹) |

The 8-bit multiplier word is the only setting that measurably costs MSE: coefficient quantization noise, largest on the harsh channel at small μ.

**T3 — update underflow.**
- The measured fraction of stalled updates agrees with a prediction computed from the L1 error and input values (e.g. B_acc = 16, μ = 2⁻¹¹: predicted 0.489, measured 0.466).
- With **round to nearest**, even 47 % stalled updates cost only +0.33 % MSE (static channel). The noise dithers the updates.
- With **truncation**, the same accumulator gives a bias: +2.1 % (μ = 2⁻⁹), +8.2 % (2⁻¹⁰), +31 % (2⁻¹¹).
- B_acc = 26 and 32: ≤ 0.3 % of updates stall; MSE unchanged.
- **The rounding rule matters more than the accumulator width in this range.**

**T4 / T4b — tracking with finite precision** (16 dB, seeds 2000–2019, paired with the final L1 data):

| μ | L1 S*_MSE | B_mul = 12 with B_acc = 16 / 26 / 32 | B_acc = 26 with B_mul = 8 / 12 / 16 |
|---|---|---|---|
| 2⁻⁶ | 10 | 10 / 10 / 10 | — |
| 2⁻⁸ | 28 | 28 / 28 / 28 | 28 / 28 / 28 |
| 2⁻¹⁰ | 112 | 112 / 112 / 112 | — |

- ρ curves agree with L1 to two decimals.
- With B_mul = 8 the excess MSE is higher at slow S (16 % against 8 % at S = 5000). The ρ-boundary is unchanged because the static baseline rises by the same amount.
- Figure `fig_P6a_T4_coefficients.png`: fixed-point and floating-point coefficient trajectories overlap while the channel moves (PPR-22 Sec. 6.2 detection method). No divergence for B_acc ≥ 16.

**T5 — FPGA-style noise generator (12 LFSRs, sum of 12 uniforms).**
- All 12 trinomials are primitive (algebraic order test). Periods 2¹⁷−1, 2¹⁸−1 and 2²⁰−1 were confirmed by simulation.
- Mean +4.6·10⁻⁴; variance 1.0011; autocorrelation ≤ 1.3·10⁻³; cross-correlation between seeds −6.7·10⁻⁴.
- Maximum 4.6σ; excess kurtosis −0.103 (Irwin–Hall −0.100).
- **Direct-detector BER on a flat channel matches the exact Irwin–Hall prediction:**

  | Eb/N0 | Measured | Irwin–Hall prediction | Gaussian | Measured / Gaussian |
  |---|---|---|---|---|
  | 6 dB | 1.933·10⁻³ | 1.933·10⁻³ | — | 0.81 |
  | 8 dB | 9.47·10⁻⁵ | 9.44·10⁻⁵ | — | 0.50 |
  | 9 dB | 9.24·10⁻⁶ | 9.28·10⁻⁶ | — | 0.27 |

  This quantifies PPR-22's 10⁻⁴ warning: below about 10⁻⁴ the bounded noise gives markedly fewer errors than Gaussian noise.

**T6 — reference vectors for RTL (P8)** (baseline (12, 26), μ = 2⁻⁸, S = 20, 14 dB, LFSR noise):
- `T6_vectors.csv`: 34000 symbols with r, d, y, e for R2 and R3 as integers.
- `T6_coeff_every100.csv`: coefficients every 100 symbols.
- `T6_vectors_README.json`: formats and settings.

**T7 — reacquisition time vs word length** (P2 large_up, μ = 2⁻⁸, 16 dB, 100 seeds):
- N_rec = 3403 symbols for L1 and for every B_mul ∈ {12, 16} with any B_acc.
- B_mul = 8 gives 2886, because its own static reference MSE is higher (0.0423 against 0.0385), which makes the threshold easier to reach. It is not faster tracking.
- A first attempt with 20 seeds gave a noise-dominated last crossing (about 47000 symbols for every configuration). It was rejected and kept as `T7_first_attempt_20seeds_INVALID.txt`.

## 3. What this means
Within the approved grid (B_mul 8–16, B_acc 16–32, round to nearest, μ ≥ 2⁻¹¹), **finite precision does not move the tracking boundary.** The boundary is set by μ and the channel, as in floating point.

The PPR-22 hypothesis that coefficient underflow restricts tracking (Sec. 6.2, Obj. 5) is therefore **not observed in this range**. The data shows where it would appear:
- truncation instead of rounding (T3: up to +31 % MSE);
- accumulators narrower than 16 bits;
- μ below 2⁻¹¹.

This is a result, not a failure. Locating the onset needs an extended grid (for example B_acc 10–14 and truncation), which is a decision for you (see `RESULTS_FINAL_L1.md` §7).

## 4. Does P6a satisfy P6? (PPR-22 Sec. 9: "Fixed-point model including the extended-precision accumulator (Sec. 6.2); reference vectors exported")
| PPR-22 commitment | Status |
|---|---|
| 6.1 explicit widths, rounding, saturation (not wraparound) | **met** (L2) |
| 6.2 extended-precision accumulator; detection by comparing fixed vs float coefficient trajectories while the channel moves | **met** (T3, T4, figure) |
| 6.3 D = 0 (no delayed adaptation) | **met by construction** |
| 4.3 LFSR noise generator and its validation (mean, variance, autocorrelation, saturation, seeds, BER effect) | **met at L2** (T5); the hardware generator is still to be built |
| 6.4 BER, N_rec and S* for each word length | **partly met.** S*_MSE: B_acc sweep at 3 μ, B_mul sweep at 1 μ. N_rec: all 9 combinations at 1 μ. BER vs word length only as a by-product. No full (μ, S, B) surface. |
| 6.4 DSP48E1, LUT, flip-flop, Fmax, slack per word length | **not part of P6** (needs synthesis, P9) |
| P6 reference vectors exported | **met** (T6) |

**Verdict: P6a covers the P6 software commitments except the full word-length × step-size × rate study of Sec. 6.4,** which is done for selected step sizes only. The resource and timing part of Sec. 6.4 belongs to P9 (hardware).

## 5. Plain-language explanation (for the viva)
- **Fixed point** means every number is an integer with an agreed position of the binary point, like money stored in paise instead of rupees. A word with B bits can hold only 2^B values, so very small changes can be lost.
- **The danger PPR-22 describes:** the LMS update μ·e·u is often tiny. If it is smaller than half of the smallest step the accumulator can store, rounding turns it into zero and that coefficient does not move ("stall").
- **What we found:** with round to nearest, stalls happen (up to 47 % of updates with a 16-bit accumulator at μ = 2⁻¹¹), but the noise makes the stalls random. On average the filter still moves correctly, so the MSE hardly changes. With truncation (always rounding down), the lost parts all point the same way, add up, and push the coefficients off target. That is why rounding matters more than width here.
- **The 8-bit multiplier word** makes the filter's coefficients coarse, which adds a small constant error. It is visible in the MSE but does not change how fast the filter can track.
- **The FPGA noise generator** adds 12 uniform random numbers, which gives a bell shape with no tails beyond 6σ. Large noise spikes are rarer than with true Gaussian noise, so measured BER is lower than the Gaussian formula when errors are rare. That is the reason for the 10⁻⁴ reporting limit.
