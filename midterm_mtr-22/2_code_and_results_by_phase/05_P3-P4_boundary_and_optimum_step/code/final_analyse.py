"""Final L1 analysis (FREEZE-1).  Runs sweep_analyse v2 on every final raw file and draws the final figures.
All results are L1 (floating point, Gaussian noise, supervised LMS).  usage: python3 final_analyse.py"""
import json, os, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sweep_analyse import analyse
from freeze_grids import MU_FLOAT, S_LIST, CHANNELS_FINAL, FINAL_SEEDS, BER14_SEEDS

RUNS = {"primary_16": ("primary", 16.0, MU_FLOAT, FINAL_SEEDS), "primary_14": ("primary", 14.0, MU_FLOAT, FINAL_SEEDS),
        "control_16": ("control", 16.0, MU_FLOAT, FINAL_SEEDS), "control_14": ("control", 14.0, MU_FLOAT, FINAL_SEEDS),
        "primary_12": ("primary", 12.0, MU_FLOAT, FINAL_SEEDS),
        "primary_14_ber14": ("primary", 14.0, [m for m in MU_FLOAT if m <= 2.0 ** -7 + 1e-15], BER14_SEEDS)}
OUT = "results/final"; os.makedirs(OUT, exist_ok=True)
A = {}
for tag, (ch, snr, mus, seeds) in RUNS.items():
    raw = f"results/final_{tag}_raw.npz"
    if not os.path.exists(raw):
        print("missing", raw); continue
    (lo, hi), nodes = CHANNELS_FINAL[ch]
    cfg = dict(channel=(lo, hi), S_list=S_LIST, mus=mus, seeds=seeds, static_seeds=seeds, static_c=nodes)
    lines = []
    def lg(s): lines.append(s)
    A[tag] = analyse(raw, cfg, snr, out_json=f"{OUT}/analysis_{tag}.json", log=lg)
    open(f"{OUT}/analysis_{tag}_log.txt", "w").write(f"FINAL L1 analysis {tag} (seeds {seeds[0]}-{seeds[-1]})\n" + "\n".join(lines))
    print("analysed", tag, flush=True)

S = np.array(S_LIST, float); FPGA = [2.0 ** -k for k in (5, 6, 7, 8, 9, 10, 11)]
lab = lambda m: f"2^-{-np.log2(m):g}"

# ---- Figure 1: BER vs S for R1, R2, R3 (selected mu), 16 and 14 dB primary
for tag in ("primary_16", "primary_14", "primary_12"):
    if tag not in A: continue
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.6), sharey=True)
    for a, mu in zip(ax, (2.0 ** -6, 2.0 ** -8, 2.0 ** -10)):
        rows = A[tag]["res"][str(mu)]["rows"]; N = np.array([r["N_bits"] for r in rows])
        for key, col, nm in (("E1", "tab:red", "R1 direct"), ("E2", "tab:orange", "R2 frozen"), ("E3", "tab:green", "R3 adaptive")):
            k = np.array([r[key] for r in rows]); ber = k / N; ub = 3.0 / N
            a.loglog(S[k > 0], ber[k > 0], "o-", color=col, ms=3, label=nm)
            if np.any(k == 0): a.scatter(S[k == 0], ub[k == 0], marker="v", color=col, s=18, label=f"{nm}: 0 errors (95% upper bound)")
        suf = np.array([r["sufficient"] for r in rows])
        ref = np.array([(r["ref_log"] if r["ref_method"] == "log" else r["ref_lin"]) for r in rows]); rub = np.array([r["ref_ub"] for r in rows])
        if suf.any(): a.loglog(S[suf], 2 * ref[suf], "k:", lw=1.2, label="2 x static reference (f = 2), resolved")
        if (~suf).any(): a.loglog(S[~suf], 2 * rub[~suf], ":", color="0.6", lw=1.2, label="2 x reference upper bound (reference-limited)")
        a.axhline(1e-4, color="0.5", ls="--", lw=0.9)
        import matplotlib.transforms as mtr
        a.text(0.98, 1.2e-4, "1e-4: limit of the planned hardware noise generator", transform=mtr.blended_transform_factory(a.transAxes, a.transData), fontsize=6.5, ha="right", color="0.35")
        a.invert_xaxis(); a.set_xlabel("S (symbols per coefficient step; smaller = faster channel)"); a.set_title(f"mu = {lab(mu)}", fontsize=10)
    ax[0].set_ylabel("BER")
    hs, ls_ = [], []
    for a in ax:
        for h, l in zip(*a.get_legend_handles_labels()):
            if l not in ls_: hs.append(h); ls_.append(l)
    ax[0].legend(hs, ls_, fontsize=6.5, loc="lower left")
    fig.suptitle(f"BER vs variation rate, {tag.replace('_', ' ')} dB (L1, ideal Gaussian noise, supervised LMS, 100 seeds)", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_ber_vs_S_{tag}.png", dpi=120); plt.close(fig)

# ---- Figure 2: rho vs S for all mu
for tag in ("primary_16", "primary_14", "control_16", "control_14"):
    if tag not in A: continue
    fig, ax = plt.subplots(figsize=(8, 5)); cm = plt.cm.viridis
    for i, mu in enumerate(MU_FLOAT):
        rows = A[tag]["res"][str(mu)]["rows"]
        ax.semilogx(S, [r["rho_traj"][0] for r in rows], "-", color=cm(i / 13), lw=1.4 if mu in FPGA else 0.7, label=lab(mu) if mu in FPGA else None)
    ax.axhline(0.5, color="k", ls="--", lw=0.8); ax.text(S[0], 0.52, "rho_th = 0.5", fontsize=8, ha="right")
    ax.invert_xaxis(); ax.set_xlabel("S (smaller = faster)"); ax.set_ylabel("tracking loss rho (0 = none, 1 = no better than a fixed filter)")
    ax.set_ylim(-0.1, 2.0); ax.legend(fontsize=7, title="mu (thick = powers of two)", title_fontsize=7)
    ax.set_title(f"Normalised tracking loss, {tag.replace('_', ' ')} dB (L1, 100 seeds)", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_rho_vs_S_{tag}.png", dpi=120); plt.close(fig)

# ---- Figure 3: tracking boundaries vs mu  (S*_BER: filled = resolved, hollow = conditional; vertical bar = transition bracket when the
#      boundary point itself is inconclusive and S*_BER is therefore not demonstrated under the frozen strict rule)
def ber_series(tags):
    out = {}
    for tag, mus_sel in tags:
        if tag not in A: continue
        for m in mus_sel:
            if str(m) in A[tag]["res"]: out[m] = A[tag]["res"][str(m)]["ber"].get("2.0", A[tag]["res"][str(m)]["ber"].get(2.0))
    return out
fig, ax = plt.subplots(1, 2, figsize=(15, 5.4))
for tag, mk, col in (("primary_16", "o", "tab:blue"), ("primary_14", "s", "tab:cyan"), ("control_16", "^", "tab:purple"), ("control_14", "v", "tab:pink")):
    if tag not in A: continue
    y = [A[tag]["res"][str(m)]["mse"]["traj_0.5"][1] for m in MU_FLOAT]
    ax[0].loglog([m for m, v in zip(MU_FLOAT, y) if v], [v for v in y if v], mk + "-", color=col, label=f"S*_MSE {tag.replace('_', ' ')} dB")
ax[0].set_title("MSE boundary S*_MSE (rho_th = 0.5)", fontsize=10)
small = [m for m in MU_FLOAT if m <= 2.0 ** -7 + 1e-15]; big = [m for m in MU_FLOAT if m > 2.0 ** -7 + 1e-15]
series = {"12 dB (100 seeds)": (ber_series([("primary_12", MU_FLOAT)]), "D", "tab:brown"),
          "14 dB (100 seeds; 1500 seeds for mu <= 2^-7)": (ber_series([("primary_14", big), ("primary_14_ber14", small)]), "s", "tab:orange"),
          "16 dB (100 seeds)": (ber_series([("primary_16", MU_FLOAT)]), "o", "tab:red")}
for nm, (ser, mk, col) in series.items():
    ms = sorted(ser); xs, ys = [], []
    for m in ms:
        b = ser[m]
        if b["S_star"]:
            filled = b["S_star_kind"] == "resolved"
            ax[1].loglog(m, b["S_star"], mk, color=col, mfc=col if filled else "none", ms=7); xs.append(m); ys.append(b["S_star"])
        elif b.get("transition_bracket") and b["primary"][S_LIST.index(b["transition_bracket"][0])] == "P":   # resolved brackets only
            lo_, hi_ = b["transition_bracket"]; ax[1].plot([m, m], [hi_, lo_], "-", color=col, lw=2.2, alpha=0.6)
    ax[1].plot([], [], mk, color=col, label=f"S*_BER primary {nm}")
ax[1].plot([], [], "k-", lw=2.2, alpha=0.5, label="bracket: boundary point inconclusive (S*_BER not demonstrated)")
ax[1].plot([], [], "ko", mfc="none", label="hollow = conditional (reference-limited passes)")
ax[1].set_xscale("log"); ax[1].set_yscale("log"); ax[1].set_title("BER boundary S*_BER (f = 2, paired seed bootstrap)", fontsize=10)
for a in ax:
    a.set_xlabel("step size mu"); a.set_ylabel("S* (larger = the receiver fails already at slower variation)"); a.legend(fontsize=7)
fig.suptitle("Tracking boundaries, primary and control channels (L1 simulation, supervised LMS)", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_boundaries_vs_mu.png", dpi=120); plt.close(fig)

# ---- Figure 4: optimum step size vs rate, and Figure 5: eps heat map
for tag in ("primary_16", "primary_14"):
    if tag not in A: continue
    mo = A[tag]["mu_opt"]; ex = A[tag]["exponent"]
    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.array([1.0 / m["S"] for m in mo]); y = np.array([m["log2mu_refined"] for m in mo]); br = np.array([m["bracketed"] and m["rho_at_opt"] <= 0.75 for m in mo])
    ax.semilogx(x[br], 2.0 ** y[br], "o", color="tab:blue", label="mu_opt (bracketed, used in the fit)"); ax.semilogx(x[~br], 2.0 ** y[~br], "x", color="0.5", label="not used (boundary or saturated)")
    sl = ex["variants"]["V0 baseline (3-pt parabola, bracketed, rho<=0.75)"][0]
    if sl:
        xx = x[br]; b0 = np.mean(y[br] - sl * np.log2(xx)); ax.semilogx(xx, 2.0 ** (b0 + sl * np.log2(xx)), "k-", lw=1, label=f"fit: slope {sl:.3f} (systematic band {ex['variants']['spread'][0]:.2f}-{ex['variants']['spread'][1]:.2f})")
        for ref, ls in ((0.5, ":"), (2 / 3, "--")):
            b1 = np.mean(y[br] - ref * np.log2(xx)); ax.semilogx(xx, 2.0 ** (b1 + ref * np.log2(xx)), ls, color="tab:red", lw=0.8, label=f"reference slope {ref:.3g}")
    ax.set_yscale("log", base=2); ax.set_xlabel("variation rate 1/S (steps per symbol)"); ax.set_ylabel("optimum step size mu_opt")
    ax.legend(fontsize=7); ax.set_title(f"Optimum step size vs variation rate, {tag.replace('_', ' ')} dB (L1)", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_mu_opt_{tag}.png", dpi=120); plt.close(fig)
    E = np.array([[A[tag]["res"][str(m)]["rows"][i]["eps3"] for m in MU_FLOAT] for i in range(len(S_LIST))])
    fig, ax = plt.subplots(figsize=(9, 5.5))
    im = ax.imshow(np.log10(E), aspect="auto", cmap="magma_r"); ax.set_xticks(range(len(MU_FLOAT))); ax.set_xticklabels([lab(m) for m in MU_FLOAT], rotation=60, fontsize=7)
    ax.set_yticks(range(len(S_LIST))); ax.set_yticklabels(S_LIST, fontsize=7); ax.set_xlabel("mu"); ax.set_ylabel("S")
    ax.plot([MU_FLOAT.index(min(MU_FLOAT, key=lambda m: abs(np.log2(m) - mm["log2mu_refined"]))) for mm in mo], range(len(S_LIST)), "c.-", lw=0.8, label="best mu per S")
    cb = fig.colorbar(im); cb.set_label("log10 excess MSE over oracle (eps)"); ax.legend(fontsize=7)
    ax.set_title(f"Step-size study: excess MSE over (mu, S), {tag.replace('_', ' ')} dB (L1, 100 seeds)", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_eps_heatmap_{tag}.png", dpi=120); plt.close(fig)
print("figures done")
