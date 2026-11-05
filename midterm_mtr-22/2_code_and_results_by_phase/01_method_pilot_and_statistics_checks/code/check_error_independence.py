"""Are R3 bit errors independent enough for binomial (Wilson) intervals?  L1 pilot-type check, 12 dB and 14 dB, seeds 5300-5399 (disjoint from pilot/final).
(a) P(error at n+k | error at n) against the overall BER; (b) burst clusters (errors closer than GAP symbols merged) -> mean errors per cluster = design effect DEFF;
(c) per-seed index of dispersion of counts (Poisson/binomial independent errors: 1)."""
import numpy as np
from exp_lib import *; from lms_lib import triangle_counter
from sweep import n_eval_for
GAP = 20
print(f"{'dB':>3s} {'S':>5s} {'mu':>8s} {'N bits':>9s} {'errors':>7s} {'BER':>8s} | P(e[n+1]|e[n]) P(e[n+2]|e[n]) | clusters  errs/cluster (DEFF) | dispersion/seed")
rows = []
for snr in (12.0, 14.0):
    for S in (1000, 80, 20, 5):
        ne = n_eval_for(S, 40, 116); c = triangle_counter(30000 + ne, 30000, 40, 116, S)
        for mu in (2.0 ** -5, 2.0 ** -7, 2.0 ** -9, 2.0 ** -11):
            seeds = range(5300, 5340); k_seed = []; clusters = 0; p1n = p1d = p2n = 0; K = 0; N = 0
            for sd in seeds:
                ex = make_exp_from_counter(c, 30000, snr, sd); yA, yF, eA, eF, _ = run_lms(ex, mu, 10 ** 9)
                e = ber_indicators(ex, yA, yF)[2][30000:]; idx = np.flatnonzero(e)
                k_seed.append(len(idx)); K += len(idx); N += len(e)
                if len(idx):
                    clusters += 1 + int((np.diff(idx) > GAP).sum())
                    p1d += len(idx) - (1 if idx[-1] == len(e) - 1 else 0)
                    p1n += int(((idx[:-1] + 1) == idx[1:]).sum()) if len(idx) > 1 else 0
                    p2n += int(np.isin(idx + 2, idx).sum())
            ks = np.array(k_seed, float)
            disp = ks.var(ddof=1) / ks.mean() if ks.mean() > 0 else float("nan")
            if K >= 20:
                print(f"{snr:3.0f} {S:5d} 2^{np.log2(mu):<5.0f} {N:9.2e} {K:7d} {K/N:8.1e} | {p1n/max(p1d,1):13.3f} {p2n/max(K,1):15.3f} | {clusters:8d}  {K/clusters:6.2f}              | {disp:6.2f}")
                rows.append((snr, S, mu, K, N, clusters))
            else:
                print(f"{snr:3.0f} {S:5d} 2^{np.log2(mu):<5.0f} {N:9.2e} {K:7d}  (too few errors, skipped)")
np.save("results/error_independence_rows.npy", np.array(rows))
