# Misadjustment of LMS with a correlated residual error — derivation, assumptions, checks (finding F-1)

Status: provisional acceptance by the project owner (20 Oct 2026); the mathematical explanation is "strongly supported", not "fully verified", until this document has been reviewed. All numbers are **L1 (floating-point) pilot results** on pilot seeds 1000–1015. V4b (textbook formula, 20 % criterion) is kept as a recorded failure; V4d is a separate test.

Code: `code/misadj_lib.py` (functions `wiener`, `gradient_noise_sums`, `exact_C`, `first_order_excess`, `lms_rows`, `linearised_mse`), `code/investigate_misadjustment.py`. Output: `code/results/misadjustment_console_log.txt`, `misadjustment_investigation.json`, `fig_M1_misadjustment_investigation.png`. Original V4b record with checksums: `code/results/original_V4b_preserved/`.

## 1. Notation
u(n) = [r(n), …, r(n−L+1)]ᵀ (L = 16), d(n) = x(n−Δ) (Δ = 2), R = E[u uᵀ] = H Hᵀ + σ² I, p = E[d u], w_o = R⁻¹p, J_min = 1 − pᵀR⁻¹p.
Optimal-filter error: e_o(n) = d(n) − w_oᵀu(n). Orthogonality gives E[e_o u] = 0, but e_o and u are **not independent**.
LMS (a-priori error, unchanged project loop): e(n) = d(n) − w(n)ᵀu(n), w(n+1) = w(n) + μ e(n) u(n).
Weight error v(n) = w(n) − w_o; gradient-noise vector g(n) = e_o(n) u(n) (zero mean).
Γ(m) = E[g(n) g(n−m)ᵀ], C(j) = tr Γ(j) = E[ e_o(n) e_o(n−j) u(n)ᵀu(n−j) ].

## 2. Exact steps
1. Since e = e_o − uᵀv: v(n+1) = (I − μ u uᵀ) v(n) + μ g(n).
2. MSE: E[e²] = J_min − 2E[g(n)ᵀ v(n)] + E[(uᵀv)²].
3. **Small-step (direct-averaging) approximation, first order in μ.** Replace u uᵀ by R in the recursion: v(n+1) = (I − μR) v(n) + μ g(n), so v(n) = μ Σ_{k≥1} (I − μR)^{k−1} g(n−k). The error of this replacement is of higher order in μ.
4. *Covariance term.* K = E[v vᵀ] satisfies, to leading order, R K + K R = μ S with S = Σ_{m=−∞}^{∞} Γ(m) (the long-run covariance of g). Taking the trace: 2 tr(RK) = μ tr S, hence E[(uᵀv)²] ≈ tr(RK) = (μ/2) [ C(0) + 2 Σ_{j≥1} C(j) ]. (u(n) is treated as independent of v(n) at this order; v(n) is dominated by terms from the distant past.)
5. *Cross term.* −2E[g(n)ᵀ v(n)] ≈ −2 μ Σ_{k≥1} E[g(n)ᵀ g(n−k)] = −2 μ Σ_{j≥1} C(j) (the factor (I − μR)^{k−1} ≈ I because Γ decays within a few lags).
6. **Result:**  J_ex = (μ/2) [ C(0) − 2 Σ_{j≥1} C(j) ].
7. Textbook (independence theory): e_o white and independent of u ⇒ C(j ≥ 1) = 0 and C(0) = J_min tr R, giving J_ex = (μ/2) J_min tr R (and q/(1 − q), q = μ tr R / 2, when the second-order term is kept as in the V4b formula).

## 3. Assumptions (all must be stated in the report)
(A1) μ small enough that step 3 holds (first order in μ). (A2) wide-sense stationarity of u and e_o; Gaussian noise. (A3) u(n) uncorrelated with v(n) at this order. (A4) Σ_j C(j) converges quickly (true: C(j) = 0 beyond j ≈ 2 for this channel). The **textbook assumption that fails** is e_o white (C(j ≥ 1) = 0).

## 4. Exact evaluation of C(j) (no simulation)
e_o(n) and every received sample are linear forms in independent zero-mean variables: data x_m (variance 1, fourth cumulant κ = −2 for ±1 symbols, 0 for Gaussian) and noise v_m (variance σ², κ = 0). For four linear forms a, b, c, d in independent variables z_k (variance s_k, fourth cumulant κ_k):
E[(a·z)(b·z)(c·z)(d·z)] = Σ_k κ_k a_k b_k c_k d_k + (Σ s a b)(Σ s c d) + (Σ s a c)(Σ s b d) + (Σ s a d)(Σ s b c).
C(j) = Σ_{i=0}^{L−1} E[ e_o(n) e_o(n−j) r(n−i) r(n−i−j) ] is evaluated with this formula (`exact_C`). No fitted parameters; inputs are h, w_o, Δ, σ².

## 5. Independent checks performed
| Check | Result |
|---|---|
| Plain-python LMS vs project numba loop (4000 symbols) | max difference 8.9e-16 |
| Separately written row-based LMS vs project loop (200000 symbols) | max difference 0.0 |
| d[n] = x[n−Δ] exactly; Wiener error by rows = by convolution | exact / 8.9e-16 |
| Fixed Wiener filter measured MSE vs J_min (8 seeds × 1e6) | 0.02734 ± 0.00004 vs 0.02736 (ratio 0.9994) |
| Steady-state window stationarity; start vs convergence time | block MSEs flat; window starts 25× after convergence |
| C(0) exact / from data / J_min tr R | 0.6058 / 0.6058 / 0.6092 |
| C(1) exact / from data | −0.1535 / −0.1535 |
| Σ_{j≥1} C(j) exact / from data (j ≤ 20) | −0.1442 / −0.1441 |
| Residual-error autocorrelation lag 1, 2, 3, 4 (white: 0 ± 0.0005) | −0.534, +0.216, −0.075, +0.023 |
| Predicted factor (C(0) − 2ΣC)/(J_min tr R) | 1.468 |
| Measured excess / textbook (16 seeds, paired, 95 % CI), μ = 2⁻⁷, 2⁻⁸, 2⁻⁹, 2⁻¹⁰ | 1.497 ± 0.003, 1.480 ± 0.003, 1.473 ± 0.003, 1.468 ± 0.004 |
| Measured / first-order exact model, same μ | 1.117, 1.055, 1.026, 1.011 (± 0.002–0.003): deviation halves with μ ⇒ second-order term |
| Time-shuffled rows (correlation removed, same LMS update), 8 records | 0.99–1.00 of textbook |
| First-order linearised LMS on the real correlated data | 1.40, 1.435, 1.450, 1.457 (→ 1.468 as μ → 0) |
| Gaussian data, ISI channel | measured/textbook 1.50, 1.49, 1.48; measured/exact (Gaussian moments) 1.064, 1.031, 1.015 |
| Flat channel (white e_o) | measured/textbook 0.996 ± 0.005; C(1) = 0; autocorrelation 0 |
| ISI-strength sweep s = 0 … 1.5 (μ = 2⁻⁹) | measured/textbook 0.996 → 1.75; model tracks within 1.5–4 % |
| Eigenvalue form Σ μλ/(2 − μλ) vs trace form | differ by 1–2 % (μ = 2⁻⁹, 2⁻¹⁰): eigenvalue spread is not the cause |

## 6. What is and is not claimed
Claimed: (i) the implementation and the measurement are correct to the stated precision; (ii) to first order in μ the excess MSE on this channel is (μ/2)(C(0) − 2ΣC(j)), and the white-error assumption of the textbook formula is what produces the 1.47 factor; (iii) the same model reproduces the measurement across ISI strengths and for Gaussian data.
Not claimed: a closed-form second-order correction (the remaining 1–6 % at μ = 2⁻¹⁰…2⁻⁸ is consistent with such a term but was not modelled); validity for time-varying channels (the derivation is for a static channel); any statement about fixed-point effects (L2).

## 7. Reviewer checklist (to defend the result)
1. Re-derive §2 steps 4 and 5 and confirm tr S = C(0) + 2ΣC(j) and the sign of the cross term.
2. Re-run `python3 investigate_misadjustment.py` (about 35 s) and compare with the log.
3. Confirm V4b still fails (checksums in `results/original_V4b_preserved/SHA256.txt`).
4. Confirm that `lms_lib.py` (which holds the unchanged LMS loop `lms_receivers`) still matches the SHA-256 recorded on 20 Oct in `results/original_V4b_preserved/lms_lib_SHA256_recorded_20Oct.txt` (recorded after the investigation; the file was not edited during it).
