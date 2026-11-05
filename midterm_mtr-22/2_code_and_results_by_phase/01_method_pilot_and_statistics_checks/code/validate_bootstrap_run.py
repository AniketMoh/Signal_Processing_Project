"""E-1 validation, data part (L1, validation seeds 300000-301999, never used elsewhere): many independent replicate experiments
with known pooled 'truth', so that the paired seed-level bootstrap can be checked for coverage and for its standard error.
12 dB, primary channel, mu in {2^-5, 2^-8}, S in {20, 1000}, plus the 11 static nodes for the paired reference (same seeds).
usage: python3 validate_bootstrap_run.py <first_seed> <n_seeds> <out.npz>"""
import sys, time, numpy as np
from sweep import run_point_full, n_eval_for
from exp_lib import *
from freeze_grids import STATIC_C
first, n, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
seeds = list(range(first, first + n)); MUS = [2.0 ** -5, 2.0 ** -8]; SNR = 12.0; NT = 30000; R = {}; t0 = time.time()
for S in (20, 1000):
    ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
    for k, v in run_point_full(c, NT, SNR, seeds, MUS).items(): R[f"{S}|{k}"] = v
    R[f"{S}|c_win"] = c[NT:].astype(np.int16)
    print(S, "done", round(time.time() - t0), flush=True)
for cc in STATIC_C:
    c = np.full(NT + 152000, cc, dtype=np.int64)
    for k, v in run_point_full(c, NT, SNR, seeds, MUS).items(): R[f"static_c{cc}|{k}"] = v
print("static done", round(time.time() - t0), flush=True)
R["seeds"] = np.array(seeds); np.savez_compressed(out, **R)
