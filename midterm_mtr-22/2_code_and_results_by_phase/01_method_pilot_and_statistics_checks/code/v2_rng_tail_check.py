"""Direct test of the noise generator tail (the V2 BER on a flat channel is exactly P(g < -x), x = sqrt(2 Eb/N0)).
2e9 standard-normal draws from numpy default_rng (same call as lms_lib.make_noise), 100 seeds x 2e7 draws; counts of g < -x at the 12 V2 points,
and of g > +x (symmetry), compared with the exact tail Q(x) (scipy.stats.norm.sf).  Run: python3 v2_rng_tail_check.py > results/v2_rng_tail_check_log.txt"""
import numpy as np, json
from scipy.stats import norm
EBN0 = np.linspace(0.0, 8.25, 12); X = np.sqrt(2 * 10 ** (EBN0 / 10))
NSEED, CH = 100, 20_000_000
lo = np.zeros(12, np.int64); hi = np.zeros(12, np.int64); tot = 0
for s in range(NSEED):
    g = np.random.default_rng(900000 + s).standard_normal(CH)
    for i, x in enumerate(X):
        lo[i] += int(np.count_nonzero(g < -x)); hi[i] += int(np.count_nonzero(g > x))
    tot += CH
Q = norm.sf(X)
print(f"{tot:.1e} draws.  x = sqrt(2 Eb/N0);  z = (count - N Q)/sqrt(N Q (1-Q))")
zl = (lo - tot * Q) / np.sqrt(tot * Q * (1 - Q)); zh = (hi - tot * Q) / np.sqrt(tot * Q * (1 - Q))
for i in range(12):
    print(f"  Eb/N0 {EBN0[i]:5.2f} dB  x={X[i]:.3f}  tail count {lo[i]:11d}  expected {tot*Q[i]:13.1f}  rel dev {lo[i]/(tot*Q[i])-1:+.2e}  z(lower) {zl[i]:+5.2f}  z(upper) {zh[i]:+5.2f}")
print(f"pooled mean z (lower tail) = {zl.mean():+.3f} (points are strongly correlated: same draws), min/max z {zl.min():+.2f}/{zl.max():+.2f}")
json.dump(dict(lo=lo.tolist(), hi=hi.tolist(), tot=tot, zl=zl.tolist(), zh=zh.tolist()), open("results/v2_rng_tail_check.json", "w"))
