"""BER-resolution study (L1 pilot). How small is the static BER of R3 at 16 dB, and how many bits are needed to resolve it?
Independent static records of 1e6 evaluation symbols (+ 30000 PRBS training), pilot seeds >= 5000 (disjoint from pilot 1000-1099 and final 2000-2099).
Run: python3 ber_resolution.py > results/ber_resolution_log.txt"""
import json, time, numpy as np
from scipy.stats import beta
from exp_lib import *

N_EV = 1_000_000; N_T = 30000
JOBS = [  # (snr, c, k for mu = 2^-k, number of records)
    (16.0, 116, 6, 100), (16.0, 116, 8, 100), (16.0, 116, 10, 100),
    (16.0, 103, 6, 50), (16.0, 103, 8, 50), (16.0, 103, 10, 50),
    (16.0, 91, 6, 50), (16.0, 91, 8, 50), (16.0, 91, 10, 50),
]


def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return lo, hi


out = []
t0 = time.time()
for snr, c, k, nrec in JOBS:
    mu = 2.0 ** -k
    cc = np.full(N_T + N_EV, c, dtype=np.int64)
    E = 0
    for r in range(nrec):
        ex = make_exp_from_counter(cc, N_T, snr, 5000 + r)
        yA, yF, eA, eF, _ = run_lms(ex, mu, 10 ** 9)
        i1, i2, i3 = ber_indicators(ex, yA, yF)
        E += int(i3[N_T:].sum())
    n = nrec * N_EV
    lo, hi = cp(E, n)
    out.append(dict(snr=snr, c=c, k=k, errors=E, bits=n, ber=E / n, lo=lo, hi=hi))
    print(f"Eb/N0 {snr:.0f} dB  c={c:3d}  mu=2^-{k:2d}:  errors {E:5d} of {n:.1e} bits  BER {E/n:.2e}  95% CI [{lo:.1e}, {hi:.1e}]   [{time.time()-t0:.0f}s]", flush=True)
json.dump(out, open("results/ber_resolution.json", "w"), indent=1)
