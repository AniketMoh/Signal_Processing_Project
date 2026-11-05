"""Check of the BER trajectory baseline at 12 dB (L1 pilot): (1) linear vs log-linear interpolation of the static BER between the 11 c nodes,
(2) direct comparison with the measured R3 BER on the slowest trajectory (S=5000, one full period, 40 seeds 5200-5239, quasi-static limit)."""
import numpy as np
from sweep import run_point, n_eval_for
from exp_lib import *; from freeze_grids import MU_FLOAT, STATIC_C
from lms_lib import triangle_counter
snr = 12.0; R = np.load("results/ber_static_grid_12.npz"); N = float(R["bits"][0])
cg = np.array(STATIC_C); cs = np.arange(40, 117); wt = np.ones(len(cs)); wt[0] = wt[-1] = 0.5; wt /= wt.sum()
P = np.array([R[f"E3_{c}"] for c in STATIC_C]).astype(float) / N
ne = n_eval_for(5000, 40, 116); seeds = list(range(5200, 5240))
c = triangle_counter(30000 + ne, 30000, 40, 116, 5000)
J2, J3, E1, E2, E3 = run_point(c, 30000, snr, seeds, MU_FLOAT)
NB = len(seeds) * ne
print(f"{'mu':>8s} {'linear interp':>14s} {'log-linear':>11s} {'ratio lin/log':>13s} {'measured S=5000':>16s} {'errors':>7s} {'meas/lin':>9s} {'meas/log':>9s}")
for i, mu in enumerate(MU_FLOAT):
    lin = np.interp(cs, cg, P[:, i]) @ wt; lg = np.exp(np.interp(cs, cg, np.log(P[:, i]))) @ wt
    k = int(E3[i].sum()); m = k / NB
    print(f"2^{np.log2(mu):5.1f} {lin:14.3e} {lg:11.3e} {lin/lg:13.2f} {m:16.3e} {k:7d} {m/lin:9.2f} {m/lg:9.2f}")
