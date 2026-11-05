"""Analyse the static BER grids: is the reference BER measurable at 12/14/16 dB, and how many bits does the final tracking run (100 seeds x N_eval) give?
Rules (P-10): reference resolved if N_bits * BER_ref,obs >= 100 (expected reference errors).  BER_ref,traj = occupancy-weighted interpolation over the 11 c values
(whole-triangle weights: interior 1/76, ends 1/152).  Static measurement itself: zero counts are flagged (upper bound 3/N), never treated as observed BER."""
import numpy as np
from freeze_grids import MU_FLOAT, STATIC_C
cg = np.array(STATIC_C); cs = np.arange(40, 117)
wt = np.ones(len(cs)); wt[0] = wt[-1] = 0.5; wt /= wt.sum()
for snr in (12, 14, 16):
    R = np.load(f"results/ber_static_grid_{snr}.npz"); N = float(R["bits"][0])
    K = np.array([R[f"E3_{c}"] for c in STATIC_C]).astype(float)       # [c, mu] errors
    p = K / N; pu = np.where(K > 0, p, 3.0 / N)
    print(f"\n=== {snr} dB: static R3 BER on 11 c-values, {N:.1e} bits each (100 seeds, 5000-5099).  zeros -> upper bound 3/N = {3/N:.1e}")
    print(f"{'mu':>8s} | BER c=40   c=76    c=116 | zero-count c-values | BER_traj obs | BER_traj UB | bits for 100 ref errors | exp. ref errors, 100 seeds: S=1000 (1.52e7)  S=5000 (7.6e7) | resolved?")
    for i, mu in enumerate(MU_FLOAT):
        pt = np.interp(cs, cg, p[:, i]) @ wt; ptu = np.interp(cs, cg, pu[:, i]) @ wt
        z = int((K[:, i] == 0).sum()); ij = {c: j for j, c in enumerate(STATIC_C)}
        need = 100 / pt if pt > 0 else np.inf
        print(f"2^{np.log2(mu):5.1f} | {p[ij[40],i]:.1e} {p[ij[72] if 72 in ij else 5,i]:.1e} {p[ij[116],i]:.1e} | {z:2d}/11 | {pt:.2e} | {ptu:.2e} | {need:.1e} | {1.52e7*pt:9.1f} {7.6e7*pt:9.1f} | {'yes' if 1.52e7*pt>=100 else 'NO '}")
