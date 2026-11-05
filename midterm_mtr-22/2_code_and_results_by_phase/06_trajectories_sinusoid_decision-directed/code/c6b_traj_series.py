# c6b_traj_series.py -- recomputes the three coefficient trajectories of c6_traj.py (same seeds, same code path) and SAVES the
# curves, so the report figure can be redrawn.  Check: the relative RMS coefficient error must equal c6.json.  Level L1.
import numpy as np, json
from config import CFG, sigma_from_ebn0
from lms_lib import triangle_counter, taps_from_counter, oracle_at
from exp_lib import make_exp_from_counter, run_lms
L = CFG["L"]; NT = 30000; ST = 8; s2 = sigma_from_ebn0(16.0) ** 2

def mean_traj(S, mu, nper=2, seeds=range(2000, 2020)):          # copied unchanged from c6_traj.py
    per = 2 * 76 * S; n_tot = NT + nper * per
    c = triangle_counter(n_tot, NT, 40, 116, S)
    W = 0
    for sd in seeds:
        ex = make_exp_from_counter(c, NT, 16.0, sd)
        W = W + run_lms(ex, mu, ST)[4]
    W = W / len(seeds)
    taps = taps_from_counter(c, CFG["h2"])
    idx = np.arange(NT + per, n_tot, ST)
    idx = idx[idx // ST < W.shape[0]]
    Wo = np.array([oracle_at(taps, n, L, 2, s2)[0] for n in idx])
    return idx, W[idx // ST], Wo, c

old = json.load(open("results/commit/c6.json")); out = {}
for S in (1000, 56, 14):
    idx, Wl, Wo, c = mean_traj(S, 2.0 ** -8)
    rel = np.sqrt(np.mean(np.sum((Wl - Wo) ** 2, 1)) / np.mean(np.sum(Wo ** 2, 1)))
    print(S, "rel error", rel, "c6.json", old[str(S)]["rel_rms_coef_error"], flush=True)
    out[f"t{S}"] = (idx - idx[0]) / (2 * 76 * S); out[f"wl{S}"] = Wl; out[f"wo{S}"] = Wo
np.savez("results/commit/c6_series.npz", **out)
print("saved")
