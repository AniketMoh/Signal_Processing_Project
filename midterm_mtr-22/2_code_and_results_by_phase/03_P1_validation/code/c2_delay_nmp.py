# c2_delay_nmp.py -- PPR-22 Sec. 5.3 commitments (level L1, floating point):
#   (a) decision-delay sweep 0 <= Delta <= L+M-2 for the non-minimum-phase preset h = [0.5, 1.0] and its minimum-phase mirror h = [1.0, 0.5]
#       (oracle/Wiener MSE and measured LMS MSE), plus the 20 % energy statement of Fig. 3;
#   (b) does the best Delta stay constant as the channel varies?  oracle MSE vs Delta along the primary and control trajectories,
#       and measured LMS MSE vs Delta on the moving channel;
#   (c) bit-alignment check of Sec. 5.3: cross-correlation of recovered and transmitted bits, peak lag against the predicted offset.
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from config import CFG, DA, sigma_from_ebn0
from lms_lib import lms_receivers, delayed_symbols, triangle_counter
from misadj_lib import wiener, simulate_static
from exp_lib import make_exp_from_counter
L = CFG["L"]; OUT = "results/commit"; log = open(f"{OUT}/c2_log.txt", "w")
def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()

# ---------------- (a) non-minimum-phase preset
s2 = sigma_from_ebn0(14.0) ** 2
lg("(a) Delta sweep, static channels, 14 dB.  oracle = Wiener MSE at that Delta; LMS = measured MSE (mu = 2^-8, 60000 symbols, last 30000 averaged, 3 seeds)")
lg(f"    Fig. 3 statement: share of x[n]'s received energy inside the window at time n for h=[0.5,1.0]: {0.5**2/(0.5**2+1.0**2):.2f}")
res_a = {}
fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
for ax, (name, h) in zip(axs, (("nmp [0.5, 1.0]", [0.5, 1.0]), ("mp [1.0, 0.5]", [1.0, 0.5]))):
    D = np.arange(0, L + len(h) - 1)
    Jo = np.array([wiener(h, d, s2)[1] for d in D])
    Jl = []
    for d in D:
        v = []
        for sd in (11, 12, 13):
            x, r = simulate_static(h, 60000, 9000 + sd, np.sqrt(s2))
            yA, yF, eA, eF, wH = lms_receivers(r, delayed_symbols(x, d), L, 2.0 ** -8, 60005, 0, 60005)
            v.append(np.mean(eA[30000:] ** 2))
        Jl.append(np.mean(v))
    Jl = np.array(Jl)
    res_a[name] = dict(Delta=D.tolist(), J_oracle=Jo.tolist(), J_lms=Jl.tolist())
    lg(f"  {name}: oracle MSE at Delta=0: {Jo[0]:.4f}, best Delta {int(D[np.argmin(Jo)])} ({Jo.min():.4f}); LMS at Delta=0: {Jl[0]:.4f}, LMS best Delta {int(D[np.argmin(Jl)])} ({Jl.min():.4f})")
    lg("     oracle " + " ".join(f"{v:.3f}" for v in Jo))
    lg("     LMS    " + " ".join(f"{v:.3f}" for v in Jl))
    ax.semilogy(D, Jo, 'o-', label='Wiener (oracle)'); ax.semilogy(D, Jl, 's--', label='LMS, measured')
    ax.set_title(f"h = {h}", fontsize=9); ax.set_xlabel('decision delay Delta'); ax.set_ylabel('MSE'); ax.legend(fontsize=8); ax.grid(alpha=.3)
fig.suptitle('Decision-delay sweep, non-minimum-phase vs minimum-phase channel, 14 dB (L1)', fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_C2a_delay_nmp.png", dpi=150); plt.close(fig)

# ---------------- (b) best Delta along the trajectories
lg("(b) best Delta along the trajectories (oracle, static channel at each counter value)")
res_b = {}
for snr in (14.0, 16.0):
    s2b = sigma_from_ebn0(snr) ** 2
    for chname, (clo, chi) in (("primary", (40, 116)), ("control", (26, 77))):
        best = []; ratio2 = []
        for c in range(clo, chi + 1):
            h = [1.0, c * DA, CFG["h2"]]
            J = np.array([wiener(h, d, s2b)[1] for d in range(0, L + 2)])
            best.append(int(np.argmin(J))); ratio2.append(J[2] / J.min())
        res_b[f"{chname}_{snr}"] = dict(best=best, ratio_D2=ratio2)
        lg(f"  {chname} {snr:.0f} dB: best Delta over c = {clo}..{chi}: min {min(best)}, max {max(best)}; MSE at Delta=2 / best MSE: max {max(ratio2):.4f}")

lg("    measured LMS MSE vs Delta on the MOVING primary channel (16 dB, mu = 2^-8, 5 seeds, N_T = 30000, evaluation over whole periods)")
res_m = {}
for S in (56, 14):
    from sweep import n_eval_for
    ne = n_eval_for(S, 40, 116, base=60000); c = triangle_counter(30000 + ne, 30000, 40, 116, S)
    row = []
    for d in range(0, 11):
        v = []
        for sd in range(2000, 2005):
            ex = make_exp_from_counter(c, 30000, 16.0, sd)
            yA, yF, eA, eF, wH = lms_receivers(ex["r"], delayed_symbols(ex["x"], d), L, 2.0 ** -8, 30000, 0, 10 ** 9)
            v.append(np.mean(eA[30000:] ** 2))
        row.append(np.mean(v))
    res_m[str(S)] = row
    lg(f"  S={S}: MSE for Delta=0..10: " + " ".join(f"{v:.4f}" for v in row) + f"  -> best Delta {int(np.argmin(row))}, MSE(2)/min {row[2]/min(row):.4f}")

# ---------------- (c) bit alignment by cross-correlation
lg("(c) cross-correlation of recovered and transmitted bits (+-1), lag = recovered index - transmitted index; peak lag vs predicted offset")
def xcorr_peak(b_hat, bits, n0, n1, lags):
    s = 2.0 * b_hat - 1; t = 2.0 * bits - 1
    v = [np.mean(s[n0:n1] * t[n0 - k:n1 - k]) for k in lags]
    return int(lags[int(np.argmax(v))]), float(max(v)), v
lags = np.arange(0, 21)
ex = make_exp_from_counter(triangle_counter(30000 + 152000, 30000, 40, 116, 1000), 30000, 14.0, 2000)
yA, yF, eA, eF, wH = lms_receivers(ex["r"], delayed_symbols(ex["x"], 2), L, 2.0 ** -8, 30000, 0, 10 ** 9)
res_c = {}
for nm, y, pred in (("R1 direct", ex["r"], 0), ("R2 frozen", yF, 2), ("R3 adaptive", yA, 2)):
    k, v, _ = xcorr_peak((y >= 0).astype(int), ex["bits"], 30100, 182000, lags)
    res_c["primary " + nm] = dict(peak=k, corr=v, predicted=pred)
    lg(f"  primary channel S=1000, 14 dB, {nm}: peak lag {k} (correlation {v:.3f}), predicted {pred}")
# non-minimum-phase static channel: R1's offset is the index of the dominant tap (1); R3 uses its best Delta from (a)
h = [0.5, 1.0]; dbest = int(np.argmin(res_a["nmp [0.5, 1.0]"]["J_oracle"]))
x, r = simulate_static(h, 80000, 9100, np.sqrt(s2)); bits = ((x + 1) / 2).astype(int)
yA, yF, eA, eF, wH = lms_receivers(r, delayed_symbols(x, dbest), L, 2.0 ** -8, 30000, 0, 10 ** 9)
for nm, y, pred in (("R1 direct", r, 1), ("R3 adaptive", yA, dbest)):
    k, v, _ = xcorr_peak((y >= 0).astype(int), bits, 30100, 80000, lags)
    res_c["nmp " + nm] = dict(peak=k, corr=v, predicted=pred)
    lg(f"  non-minimum-phase h=[0.5,1.0], 14 dB, {nm}: peak lag {k} (correlation {v:.3f}), predicted {pred}")
json.dump(dict(a=res_a, b=res_b, moving=res_m, c=res_c), open(f"{OUT}/c2.json", "w"))
