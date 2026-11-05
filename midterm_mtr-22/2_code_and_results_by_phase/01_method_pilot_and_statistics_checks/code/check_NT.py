"""FREEZE-1 check 1 (L1 pilot data): is N_T = 30000 enough for every mu?  Static channel c=40 (training channel), 16 dB (slowest case: smallest sigma^2).
Compared with the Wiener reference: (a) mean-weight distance ||E[w(N_T)] - w_o||^2 / ||w_o||^2, (b) excess MSE over the last 5000 training symbols vs the steady state
measured 100000-200000 symbols later, (c) the analytic mean-weight transient prediction. Seeds 1000-1039 (pilot)."""
import json, numpy as np
from exp_lib import *; from freeze_grids import MU_FLOAT
from misadj_lib import wiener
snr = 16.0; s2 = sigma_from_ebn0(snr) ** 2; c0 = 40; NT = 30000; NTOT = 200000; stride = 500; seeds = list(range(1000, 1040))
h = taps_from_counter(np.array([c0]), H2)[0]; wo, Jmin, R = wiener(h, DELTA, s2); lam = np.linalg.eigvalsh(R)
print(f"c={c0}, 16 dB: J_min {Jmin:.5f}  lambda_min {lam[0]:.4f}  lambda_max {lam[-1]:.3f}  ||w_o||^2 {wo@wo:.3f}")
c = np.full(NTOT, c0, dtype=np.int64); out = {}
print(f"{'mu':>9s} {'1/(2 mu lmin)':>14s} {'model ||Ew-wo||^2/||wo||^2 @NT':>31s} {'meas. @NT':>10s} {'meas. @NT/2':>11s} {'excess@NT-5000..NT':>19s} {'excess steady':>14s} {'ratio':>6s}")
for mu in MU_FLOAT:
    W = []; Ew = 0
    for sd in seeds:
        ex = make_exp_from_counter(c, NT, snr, sd); yA, yF, eA, eF, wH = run_lms(ex, mu, stride)
        W.append(wH); Ew = Ew + eA ** 2
    W = np.array(W); Ew = Ew / len(seeds); wm = W.mean(axis=0)
    dist = ((wm - wo) ** 2).sum(axis=1) / (wo @ wo)
    iN = NT // stride; iH = iN // 2
    # model: mean weight starts at 0 -> ||E w - wo||^2 = sum_i (q_i.wo)^2 (1-mu lam_i)^(2n)
    lamE, Q = np.linalg.eigh(R); proj = (Q.T @ wo) ** 2
    model = float((proj * (1 - mu * lamE) ** (2 * NT)).sum() / (wo @ wo))
    ex_nt = (Ew[NT - 5000:NT].mean() - Jmin) / Jmin; ex_ss = (Ew[100000:].mean() - Jmin) / Jmin
    # excess MSE is noisy: also use block means over 5000 for the same stationarity statement
    print(f"{mu:9.2e} {1/(2*mu*lam[0]):14.0f} {model:31.2e} {dist[iN-1]:10.2e} {dist[iH-1]:11.2e} {100*ex_nt:18.1f}% {100*ex_ss:13.1f}% {ex_nt/ex_ss:6.2f}")
    out[str(mu)] = dict(tau=1/(2*mu*lam[0]), model_dist=model, meas_dist=float(dist[iN-1]), ex_nt=float(ex_nt), ex_ss=float(ex_ss))
json.dump(out, open("results/check_NT.json", "w"))
