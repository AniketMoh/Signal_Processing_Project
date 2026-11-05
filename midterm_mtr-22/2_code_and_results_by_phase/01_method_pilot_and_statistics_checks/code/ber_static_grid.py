"""FREEZE-1 check 2 (L1 pilot data): static R3 BER on the 11-point c grid, all 14 mu, 100 seeds (5000-5099, disjoint from pilot/final seeds), 152000 symbols after training.
usage: python3 ber_static_grid.py <snr_dB>"""
import sys, numpy as np
from sweep import run_point
from exp_lib import *; from freeze_grids import MU_FLOAT, STATIC_C
snr = float(sys.argv[1]); seeds = list(range(5000, 5100)); R = {}
for cc in STATIC_C:
    c = np.full(30000 + 152000, cc, dtype=np.int64)
    J2, J3, E1, E2, E3 = run_point(c, 30000, snr, seeds, MU_FLOAT)
    R[f"E3_{cc}"] = E3.sum(axis=1); R[f"E1_{cc}"] = E1.sum(axis=1); R[f"J3_{cc}"] = J3.mean(axis=1)
    print(snr, cc, "done", flush=True)
R["bits"] = np.array([len(seeds) * 152000]); np.savez(f"results/ber_static_grid_{snr:.0f}.npz", **R)
