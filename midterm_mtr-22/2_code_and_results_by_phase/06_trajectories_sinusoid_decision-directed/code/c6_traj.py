# c6_traj.py -- PPR-22 Sec. 5.7 / 10.2 "Trajectories": LMS coefficients w_k[n] overlaid on the known (oracle) optimum trajectory,
# continuous triangular variation, primary channel, 16 dB, supervised LMS, Delta = 2.  Level L1.
# The mean coefficient trajectory over 20 seeds is used (the channel trajectory is identical for all seeds, only bits and noise differ).
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from config import CFG, sigma_from_ebn0
from lms_lib import triangle_counter, taps_from_counter, oracle_at
from exp_lib import make_exp_from_counter, run_lms
L = CFG["L"]; OUT = "results/commit"; NT = 30000; ST = 8; s2 = sigma_from_ebn0(16.0) ** 2
log = open(f"{OUT}/c6_log.txt", "w")
def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()

def mean_traj(S, mu, nper=2, seeds=range(2000, 2020)):
    per = 2 * 76 * S; n_tot = NT + nper * per
    c = triangle_counter(n_tot, NT, 40, 116, S)
    W = 0
    for sd in seeds:
        ex = make_exp_from_counter(c, NT, 16.0, sd)
        W = W + run_lms(ex, mu, ST)[4]
    W = W / len(seeds)
    taps = taps_from_counter(c, CFG["h2"])
    idx = np.arange(NT + per, n_tot, ST)                     # second period only (first period removes the start transient)
    idx = idx[idx // ST < W.shape[0]]
    Wo = np.array([oracle_at(taps, n, L, 2, s2)[0] for n in idx])
    return idx, W[idx // ST], Wo, c

def best_shift(a, b):
    # delay s (in stored samples) that best aligns the LMS curve b with the oracle curve a: min over s of mean((b[n+s] - a[n])^2)
    sh = np.arange(0, len(a) // 4)
    err = [np.mean((b[s:] - a[:len(a) - s]) ** 2) for s in sh]
    return int(sh[int(np.argmin(err))])

res = {}
fig, axs = plt.subplots(3, 1, figsize=(8, 8.5), sharex=False)
for ax, S in zip(axs, (1000, 56, 14)):
    mu = 2.0 ** -8
    idx, Wl, Wo, c = mean_traj(S, mu)
    rel = np.sqrt(np.mean(np.sum((Wl - Wo) ** 2, 1)) / np.mean(np.sum(Wo ** 2, 1)))
    var_tap = np.argsort(np.ptp(Wo, axis=0))[::-1][:3]        # the three taps that move most
    lags = []
    for k in var_tap:
        lags.append(best_shift(Wo[:, k], Wl[:, k]) * ST)
    res[str(S)] = dict(rel_rms_coef_error=float(rel), moving_taps=var_tap.tolist(), lag_symbols=lags,
                       ptp_oracle=[float(np.ptp(Wo[:, k])) for k in var_tap], ptp_lms=[float(np.ptp(Wl[:, k])) for k in var_tap])
    lg(f"S={S:5d}, mu=2^-8: relative RMS coefficient error {rel:.3f}; most moving taps {var_tap.tolist()}; lag (symbols) {lags}; "
       f"swing oracle {[round(x,3) for x in res[str(S)]['ptp_oracle']]} vs LMS {[round(x,3) for x in res[str(S)]['ptp_lms']]}")
    t = (idx - idx[0]) / (2 * 76 * S)
    for j, k in enumerate(var_tap):
        col = ['#1f77b4', '#d62728', '#2ca02c'][j]
        ax.plot(t, Wo[:, k], '-', color=col, lw=1.2, label=f'oracle w*_{k}' if True else None)
        ax.plot(t, Wl[:, k], '--', color=col, lw=1.2, label=f'LMS w_{k} (mean of 20 seeds)')
    ax.set_title(f"S = {S}  (mu = 2^-8; S*_MSE = 28 at 16 dB)", fontsize=9); ax.set_xlabel('time / period'); ax.set_ylabel('coefficient'); ax.grid(alpha=.3)
axs[0].legend(fontsize=7, ncol=3)
fig.suptitle('Coefficient trajectories vs the optimum, primary channel, 16 dB, supervised LMS (L1)', fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_C6_trajectories.png", dpi=150); plt.close(fig)

lg("lag vs step size at S = 1000 (slow ramp): lag should scale as 1/mu")
for p in (6, 7, 8, 9, 10):
    idx, Wl, Wo, c = mean_traj(1000, 2.0 ** -p, seeds=range(2000, 2010))
    k = int(np.argmax(np.ptp(Wo, axis=0)))
    lag = best_shift(Wo[:, k], Wl[:, k]) * ST
    res[f"lag_p{p}"] = dict(tap=k, lag=lag)
    lg(f"  mu=2^-{p}: tap {k}, lag {lag} symbols, lag*mu = {lag * 2.0 ** -p:.2f}")
json.dump(res, open(f"{OUT}/c6.json", "w"))
