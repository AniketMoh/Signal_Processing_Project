# p6c_fig.py -- figure of the L2 word-length surface: S*_MSE against step size for each word-length configuration (16 dB, 20 seeds).
import json, os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
P = list(range(5, 12))
def get(fam, key):
    out = []
    for p in P:
        r = json.load(open(f"results/p6c/surface_{fam}_{p}.json")).get(key)
        out.append(np.nan if (r is None or "u" in r["status"] or r["S_star"] is None) else r["S_star"])
    return np.array(out, float)
fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
mu = 2.0 ** -np.array(P)
for ax, fam, rnd, title, confs in ((axs[0], "A", 1, "accumulator width, round to nearest", [(26, 12), (16, 12), (14, 12), (12, 12), (10, 10)]),
                                   (axs[1], "A", 0, "accumulator width, truncation", [(26, 12), (16, 12), (14, 12), (12, 12), (10, 10)]),
                                   (axs[2], "B", None, "multiplier width (B_acc = 26)", [(26, 16), (26, 12), (26, 8)])):
    for ba, bm in confs:
        for rr in ((rnd,) if rnd is not None else (1, 0)):
            y = get(fam, f"{ba}|{bm}|{rr}")
            lab = f"B_acc {ba} / B_mul {bm}" + ("" if rnd is not None else (", nearest" if rr else ", trunc"))
            ax.loglog(mu, y, 'o-' if rr else 's--', label=lab)
    ax.set_xlabel('step size mu'); ax.set_title(title, fontsize=9); ax.grid(alpha=.3, which='both'); ax.legend(fontsize=7)
axs[0].set_ylabel('S*_MSE (smaller = faster channel tracked)')
fig.suptitle('Tracking boundary against word length, primary channel, 16 dB, 20 seeds (L2, bit-true fixed point). Missing points: rho undefined (filter fails even on a static channel)', fontsize=8.5)
fig.tight_layout(); fig.savefig('results/p6c/fig_P6_surface.png', dpi=150)
