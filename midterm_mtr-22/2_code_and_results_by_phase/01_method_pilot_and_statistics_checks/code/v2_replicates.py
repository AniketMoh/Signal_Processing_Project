"""V2 revised, arbitration of the sign-check flag.  The replicate with seeds 17000/18000 passed the intervals and the pooled chi-square but
11 of 12 points lay above theory (sign test p = 0.006).  Procedure fixed BEFORE this run: 20 further independent replicates (new seeds);
(i) pooled mean of all 240 z-values against 0 (standard error 1/sqrt(240)), alpha = 0.01 two-sided;
(ii) pooled chi-square of all z^2 against chi2(240), alpha = 0.01 two-sided;
(iii) per Eb/N0 point: mean z over the 20 replicates (standard error 1/sqrt(20)), Bonferroni alpha = 0.05/12;
(iv) number of replicates failing each single-run criterion, compared with its nominal false-alarm rate.
Single-run failures are INCONCLUSIVE (the rule was tightened to this wording after the first replicate flag, following the project owner's instruction not to declare a bug from one excursion).
Run: python3 v2_replicates.py > results/v2_replicates_log.txt"""
import json, numpy as np
from scipy.stats import norm, chi2, binomtest, beta
from config import sigma_from_ebn0
from lms_lib import make_bits, bpsk, make_noise, bpsk_theory

EBN0 = np.linspace(0.0, 8.25, 12); N = 2_000_000; R = 20; M = 12
Z = np.zeros((R, M)); K = np.zeros((R, M), int)
P = np.array([float(bpsk_theory(e)) for e in EBN0])
for rep in range(R):
    for i, e in enumerate(EBN0):
        bits = make_bits(N, 20000 + 100 * rep + i)
        r = bpsk(bits) + make_noise(N, sigma_from_ebn0(e), 30000 + 100 * rep + i)
        k = int(np.sum((r >= 0).astype(int) != bits)); K[rep, i] = k
        Z[rep, i] = (k - N * P[i]) / np.sqrt(N * P[i] * (1 - P[i]))
z = Z.ravel()
mz = z.mean(); se = 1 / np.sqrt(len(z)); p_mean = 2 * norm.sf(abs(mz) / se)
chi = float((z ** 2).sum()); p_chi = 2 * min(chi2.sf(chi, len(z)), chi2.cdf(chi, len(z)))
pm = Z.mean(axis=0) * np.sqrt(R); p_pt = 2 * norm.sf(np.abs(pm))
print(f"{R} independent replicates x 12 points (2e6 bits each, min errors {K.min()})")
print(f"(i)  pooled mean z = {mz:+.3f}, standard error {se:.3f}, p = {p_mean:.3f}   -> {'no bias detected' if p_mean > 0.01 else 'BIAS FLAG'}")
print(f"(ii) pooled chi2 = {chi:.1f} for {len(z)} dof (expected {len(z)} +- {np.sqrt(2*len(z)):.0f}), two-sided p = {p_chi:.3f}   -> {'consistent' if p_chi > 0.01 else 'FLAG'}")
print("(iii) per-point mean z over replicates (z-score of the mean, p):")
for i, e in enumerate(EBN0):
    print(f"      {e:5.2f} dB: mean z {Z[:, i].mean():+.2f}  scaled {pm[i]:+.2f}  p {p_pt[i]:.3f}  {'FLAG' if p_pt[i] < 0.05/12 else ''}")
# single-run criteria per replicate
fl_chi = fl_sign = fl_int = 0
for rep in range(R):
    zz = Z[rep]; c = (zz ** 2).sum(); fl_chi += chi2.sf(c, M) < 0.01
    npos = int((zz > 0).sum()); fl_sign += binomtest(npos, M, 0.5).pvalue < 0.01
    lo = beta.ppf(0.05 / M / 2, K[rep], N - K[rep] + 1); hi = beta.ppf(1 - 0.05 / M / 2, K[rep] + 1, N - K[rep])
    fl_int += not np.all((lo <= N * P / N) & (N * P / N <= hi))
print(f"(iv) replicates failing a single-run criterion (nominal false-alarm rates 1 %, 1 %, 5 %): pooled chi2 {fl_chi}/{R}, sign test {fl_sign}/{R}, familywise intervals {fl_int}/{R}")
json.dump(dict(Z=Z.tolist(), K=K.tolist(), mean_z=float(mz), p_mean=float(p_mean), chi2=chi, p_chi=float(p_chi), flags=dict(chi=int(fl_chi), sign=int(fl_sign), intervals=int(fl_int))), open("results/v2_replicates.json", "w"))
