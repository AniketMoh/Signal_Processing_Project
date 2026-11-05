"""V2 revised (P-11, approved with correction).  Flat channel, no ISI, direct detector, 12 Eb/N0 points, 2e6 bits each.
Original V2 (in p1_validation.py, results/p1_results.json) is NOT modified; the same data (seeds 7000+i, 8000+i) are re-evaluated here,
and an independent replicate with new seeds (17000+i, 18000+i) is run.
Predeclared procedure:
  (a) familywise level alpha_FW = 0.05, Bonferroni: per-point exact (Clopper-Pearson) interval of level 1 - alpha_FW/12 = 99.583 %;
  (b) pooled check against a global systematic deviation: chi2 = sum z_i^2 (z_i = (k_i - N p_i)/sqrt(N p_i (1-p_i))), p-value from chi2 with 12 dof, alpha = 0.01;
  (c) sign check: number of points with k_i above N p_i, two-sided binomial test against 1/2, alpha = 0.01;
  (d) at least 100 observed errors per point.
V2 passes if (a)-(d) hold. A failing run is repeated once with different seeds; a failure is called systematic only if it fails again or (b)/(c) fail.
Run: python3 v2_revised.py > results/v2_revised_log.txt"""
import json, numpy as np
from scipy.stats import binomtest, chi2, beta
from config import sigma_from_ebn0
from lms_lib import make_bits, bpsk, make_noise, bpsk_theory

EBN0 = np.linspace(0.0, 8.25, 12); N = 2_000_000; ALPHA_FW = 0.05; M = 12


def cp(k, n, a):
    return (0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)), (1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k))


def run(seed_bits, seed_noise, label):
    rows = []; ks = []; ps = []
    for i, e in enumerate(EBN0):
        bits = make_bits(N, seed_bits + i)
        r = bpsk(bits) + make_noise(N, sigma_from_ebn0(e), seed_noise + i)
        k = int(np.sum((r >= 0).astype(int) != bits)); p0 = float(bpsk_theory(e))
        l95, h95 = cp(k, N, 0.05); l99, h99 = cp(k, N, 0.01); lb, hb = cp(k, N, ALPHA_FW / M)
        z = (k - N * p0) / np.sqrt(N * p0 * (1 - p0))
        rows.append(dict(ebn0=float(e), errors=k, ber=k / N, theory=p0, in95=bool(l95 <= p0 <= h95), in99=bool(l99 <= p0 <= h99), inFW=bool(lb <= p0 <= hb), z=float(z), lo_fw=lb, hi_fw=hb))
        ks.append(k); ps.append(p0)
    z = np.array([r["z"] for r in rows])
    chi = float((z ** 2).sum()); p_chi = float(chi2.sf(chi, M))
    n_pos = int((z > 0).sum()); p_sign = float(binomtest(n_pos, M, 0.5).pvalue)
    a = all(r["inFW"] for r in rows); d = min(r["errors"] for r in rows) >= 100
    passed = a and (p_chi > 0.01) and (p_sign > 0.01) and d
    print(f"\n[{label}]  seeds {seed_bits}+i / {seed_noise}+i")
    for r in rows:
        print(f"   Eb/N0 {r['ebn0']:5.2f} dB  errors {r['errors']:7d}  BER {r['ber']:.3e}  theory {r['theory']:.3e}  z {r['z']:+5.2f}  in95 {r['in95']!s:5}  in99 {r['in99']!s:5}  in familywise {r['inFW']!s:5}")
    print(f"   inside 95 %: {sum(r['in95'] for r in rows)}/12   inside 99 %: {sum(r['in99'] for r in rows)}/12   inside familywise (99.583 %): {sum(r['inFW'] for r in rows)}/12")
    print(f"   (b) pooled chi2 = {chi:.2f} (12 dof), p = {p_chi:.3f}   (c) points above theory: {n_pos}/12, sign-test p = {p_sign:.3f}   (d) min errors {min(r['errors'] for r in rows)}")
    print(f"   REVISED V2 verdict: {'PASS' if passed else 'FAIL'}")
    return dict(rows=rows, chi2=chi, p_chi=p_chi, n_pos=n_pos, p_sign=p_sign, passed=bool(passed))


orig = run(7000, 8000, "ORIGINAL DATA re-evaluated (same seeds as the original V2)")
repl = run(17000, 18000, "INDEPENDENT REPLICATE (new seeds)")
json.dump(dict(original_data=orig, replicate=repl, alpha_FW=ALPHA_FW), open("results/v2_revised.json", "w"), indent=1)
