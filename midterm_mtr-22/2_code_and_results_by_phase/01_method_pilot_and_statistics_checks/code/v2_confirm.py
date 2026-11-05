"""V2 confirmation of the pooled-bias flag.  Predeclared before running: 100 NEW independent replicates (seeds 40000+..., 60000+...) of the V2 pipeline
(make_bits, make_noise, error count), 12 points x 2e6 bits; the flag is CONFIRMED only if these new data alone give a pooled mean z with
p < 0.01 (two-sided) in the same (positive) direction; otherwise the earlier flag is recorded as an unconfirmed statistical excursion.
Run: python3 v2_confirm.py > results/v2_confirm_log.txt"""
import json, numpy as np
from scipy.stats import norm, chi2
from config import sigma_from_ebn0
from lms_lib import make_bits, bpsk, make_noise, bpsk_theory
EBN0 = np.linspace(0.0, 8.25, 12); N = 2_000_000; R = 100
P = np.array([float(bpsk_theory(e)) for e in EBN0])
Z = np.zeros((R, 12))
for rep in range(R):
    for i, e in enumerate(EBN0):
        bits = make_bits(N, 40000 + 100 * rep + i)
        r = bpsk(bits) + make_noise(N, sigma_from_ebn0(e), 60000 + 100 * rep + i)
        k = int(np.sum((r >= 0).astype(int) != bits))
        Z[rep, i] = (k - N * P[i]) / np.sqrt(N * P[i] * (1 - P[i]))
z = Z.ravel(); mz = z.mean(); se = 1 / np.sqrt(len(z)); p = 2 * norm.sf(abs(mz) / se)
chi = float((z ** 2).sum()); pchi = 2 * min(chi2.sf(chi, len(z)), chi2.cdf(chi, len(z)))
pm = Z.mean(axis=0) * np.sqrt(R)
print(f"{R} replicates x 12 points ({R*12*N:.1e} bits)")
print(f"pooled mean z = {mz:+.4f}, standard error {se:.4f}, p = {p:.3f}   -> {'BIAS CONFIRMED' if (p < 0.01 and mz > 0) else 'not confirmed'}")
print(f"pooled chi2 = {chi:.1f} for {len(z)} dof (expected {len(z)} +- {np.sqrt(2*len(z)):.0f}), two-sided p = {pchi:.3f}")
print("per-point scaled mean z:", np.round(pm, 2))
# combined with the 20-replicate set (different seeds)
Z0 = np.array(json.load(open("results/v2_replicates.json"))["Z"]); zc = np.concatenate([z, Z0.ravel()]); mc = zc.mean(); sc = 1 / np.sqrt(len(zc))
print(f"for the record, all {len(zc)//12} replicates pooled (20 + {R}): mean z {mc:+.4f}, standard error {sc:.4f}, p = {2*norm.sf(abs(mc)/sc):.3f}")
json.dump(dict(Z=Z.tolist(), mean_z=float(mz), p=float(p), chi2=chi, p_chi=float(pchi)), open("results/v2_confirm.json", "w"))
