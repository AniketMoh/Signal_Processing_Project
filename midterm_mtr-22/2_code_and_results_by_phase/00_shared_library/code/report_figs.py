"""report_figs.py -- redraws the report figures in one style (report_style.py) from the SAVED result files.
No experiment is rerun and no number is changed: every value is read from results/... .
usage: python3 report_figs.py [name ...]      (no name = all figures)   output: results/report_figs/*.pdf|png"""
import json, sys, numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as mtr
import report_style as st
from report_style import R1, R2, R3, RX, RXNAME, THEORY, GREY, PRIMARY, CONTROL
st.apply()

S_LIST = [5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1]
MU_FLOAT = [2.0 ** -(5 + 0.5 * i) for i in range(14)]
FPGA = [2.0 ** -k for k in range(5, 12)]
A = {}
def an(tag):
    if tag not in A: A[tag] = json.load(open(f"results/final/analysis_{tag}.json"))
    return A[tag]
def mkey(res, mu):
    for k in res:
        if abs(float(k) - mu) < 1e-12: return k
    raise KeyError(mu)

def xS(ax):
    ax.set_xscale("log"); ax.invert_xaxis()
    ax.set_xlabel(r"$S$, symbols per coefficient step (faster $\rightarrow$)")

FIGS = {}
def fig(f): FIGS[f.__name__] = f; return f

# ------------------------------------------------------------------ BER against variation rate (P3)
@fig
def ber_vs_S():
    d = an("primary_14")
    S = np.array(S_LIST, float)
    f, axs = plt.subplots(1, 3, figsize=(st.TXT_W, 2.25), sharey=True)
    for i, (ax, mu) in enumerate(zip(axs, (2.0 ** -6, 2.0 ** -8, 2.0 ** -10))):
        rows = d["res"][mkey(d["res"], mu)]["rows"]; N = np.array([r["N_bits"] for r in rows], float)
        for key, rx in (("E1", "R1"), ("E2", "R2"), ("E3", "R3")):
            k = np.array([r[key] for r in rows], float); ber = k / N
            ax.plot(S[k > 0], ber[k > 0], "-o", color=RX[rx], ms=2.6, lw=1.3, label=RXNAME[rx])
            if np.any(k == 0):
                ax.plot(S[k == 0], 3.0 / N[k == 0], "v", color=RX[rx], mfc="white", ms=3.5, label="zero errors (95 % upper bound)" if rx == "R3" else None)
        suf = np.array([r["sufficient"] for r in rows])
        ref = np.array([(r["ref_log"] if r["ref_method"] == "log" else r["ref_lin"]) for r in rows]); rub = np.array([r["ref_ub"] for r in rows])
        if suf.any(): ax.plot(S[suf], 2 * ref[suf], ":", color=THEORY, lw=1.0, label=r"$2\times$ static R3 BER ($S^\star_{\rm BER}$ threshold)")
        if (~suf).any(): ax.plot(S[~suf], 2 * rub[~suf], ":", color=GREY, lw=1.0, label=r"$2\times$ reference upper bound")
        ax.axhline(1e-4, color=GREY, ls="--", lw=0.7)
        if i == 0: ax.text(0.03, 1.3e-4, r"$10^{-4}$: 12-uniform noise no longer Gaussian-like", transform=mtr.blended_transform_factory(ax.transAxes, ax.transData), fontsize=6, color="#555555")
        ax.set_yscale("log"); xS(ax); ax.set_title(r"$\mu=$" + st.mu_label(mu)); st.panel(ax, "abc"[i])
        if i != 1: ax.set_xlabel("")
        b = d["res"][mkey(d["res"], mu)]["mse"]["traj_0.5"][1]
        if b: ax.axvline(b, color=R3, lw=0.8, alpha=0.35); ax.text(b, 0.93, r" $S^{\star}_{\rm MSE}$", color=R3, fontsize=6.5, va="top", transform=mtr.blended_transform_factory(ax.transData, ax.transAxes))
    axs[0].set_ylabel("bit-error rate"); axs[0].set_ylim(5e-8, 0.5)
    h, l = [], []
    for ax in axs:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            if ll not in l: h.append(hh); l.append(ll)
    f.tight_layout(w_pad=0.8, rect=(0, 0, 1, 0.86))
    f.legend(h, l, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), fontsize=6.5)
    st.save(f, "ber_vs_S")

# ------------------------------------------------------------------ tracking loss rho: curves + map (P3)
@fig
def rho():
    d = an("primary_16"); S = np.array(S_LIST, float)
    f, (a1, a2) = plt.subplots(1, 2, figsize=(st.TXT_W, 2.45), gridspec_kw=dict(width_ratios=[1, 1.15]))
    cols = st.blues(len(MU_FLOAT))
    R = np.full((len(S_LIST), len(MU_FLOAT)), np.nan)
    for j, mu in enumerate(MU_FLOAT):
        rows = d["res"][mkey(d["res"], mu)]["rows"]; r = np.array([x["rho_traj"][0] for x in rows], float); R[:, j] = r
        a1.plot(S, r, "-", color=cols[j], lw=1.3 if mu in FPGA else 0.6, label=st.mu_label(mu) if mu in FPGA else None)
    a1.axhline(0.5, color=THEORY, ls="--", lw=0.8); a1.text(4000, 0.55, r"$\rho_{\rm th}=0.5$", fontsize=6.5)
    xS(a1); a1.set_ylim(-0.1, 1.6); a1.set_ylabel(r"tracking loss $\rho$"); st.leg_below(a1, ncol=4, title=r"$\mu$ (thin lines: half steps)", title_fontsize=6.3)
    st.panel(a1, "a")
    im = a2.imshow(np.clip(R, 0, 1.2), aspect="auto", cmap="Blues", vmin=0, vmax=1.2, origin="upper")
    a2.set_xticks(range(len(MU_FLOAT))); a2.set_xticklabels([st.mu_label(m) if m in FPGA else "" for m in MU_FLOAT])
    a2.set_yticks(range(0, len(S_LIST), 2)); a2.set_yticklabels(S_LIST[::2], fontsize=6.5)
    a2.set_xlabel(r"step size $\mu$"); a2.set_ylabel(r"$S$ (faster $\downarrow$)"); a2.grid(False)
    bx, by = [], []
    for j, mu in enumerate(MU_FLOAT):
        b = d["res"][mkey(d["res"], mu)]["mse"]["traj_0.5"][1]
        if b in S_LIST: bx.append(j); by.append(S_LIST.index(b))
    a2.step(bx, by, where="mid", color=R1, lw=1.4, label=r"$S^\star_{\rm MSE}$ (fastest passing $S$)")
    st.leg_below(a2, ncol=1)
    cb = f.colorbar(im, ax=a2, fraction=0.05, pad=0.02); cb.set_label(r"$\rho$ (clipped at 1.2)"); cb.outline.set_linewidth(0.4)
    st.panel(a2, "b")
    f.tight_layout(w_pad=1.5); st.save(f, "rho")

# ------------------------------------------------------------------ boundaries against mu (P3)
def ber_series(pairs):
    out = {}
    for tag, mus in pairs:
        d = an(tag)
        for m in mus:
            try: k = mkey(d["res"], m)
            except KeyError: continue
            b = d["res"][k]["ber"]; out[m] = b.get("2.0", b.get(2.0))
    return out

@fig
def boundaries():
    f, (a1, a2) = plt.subplots(1, 2, figsize=(st.TXT_W, 2.7))
    mm = np.array(MU_FLOAT)
    a1.plot(mm, 0.1095 / mm, "--", color=THEORY, lw=0.8, label=r"$S^{\star}\mu=0.11$")
    a1.text(3.5e-4, 12, "all four cases coincide\nfor $\\mu\\leq2^{-7.5}$", fontsize=6.5, color="#333333")
    for tag, col, mk, fill, lsty in (("primary_16", PRIMARY, "o", True, "-"), ("primary_14", PRIMARY, "o", False, ":"),
                                     ("control_16", CONTROL, "s", True, "-"), ("control_14", CONTROL, "s", False, ":")):
        d = an(tag); y = [d["res"][mkey(d["res"], m)]["mse"]["traj_0.5"][1] for m in MU_FLOAT]
        xs = [m for m, v in zip(MU_FLOAT, y) if v]; ys = [v for v in y if v]
        a1.plot(xs, ys, lsty, color=col, lw=0.9); a1.plot(xs, ys, mk, color=col, mfc=col if fill else "white", ms=3.6,
                label=f"{tag.split('_')[0]} {tag.split('_')[1]} dB")
    a1.set_xscale("log"); a1.set_yscale("log"); a1.set_xlabel(r"step size $\mu$"); a1.set_ylabel(r"boundary $S^\star$ (symbols per step)")
    a1.set_title(r"MSE boundary $S^\star_{\rm MSE}$ ($\rho_{\rm th}=0.5$)"); st.leg_below(a1, ncol=3); st.panel(a1, "a")
    small = [m for m in MU_FLOAT if m <= 2.0 ** -7 + 1e-15]; big = [m for m in MU_FLOAT if m > 2.0 ** -7 + 1e-15]
    ser = {"12 dB": (ber_series([("primary_12", MU_FLOAT)]), "D", "#1baf7a"),
           "14 dB": (ber_series([("primary_14", big), ("primary_14_ber14", small)]), "s", "#eda100"),
           "16 dB": (ber_series([("primary_16", MU_FLOAT)]), "o", "#e34948")}
    off = {"12 dB": 0.93, "14 dB": 1.0, "16 dB": 1.07}
    for nm, (s, mk, col) in ser.items():
        for m in sorted(s):
            b = s[m]; x = m * off[nm]
            if b["S_star"]:                                   # boundary demonstrated
                a2.plot(x, b["S_star"], mk, color=col, mfc=col if b["S_star_kind"] == "resolved" else "white", ms=4.2, mew=1.0)
            elif b.get("transition_bracket"):                 # boundary point inconclusive: only the bracket is known
                lo_, hi_ = b["transition_bracket"]; resolved_end = b["primary"][S_LIST.index(lo_)] == "P"
                a2.plot([x, x], [hi_, lo_], ls="-" if resolved_end else (0, (1.2, 1.2)), color=col, lw=2.2 if resolved_end else 1.6,
                        alpha=0.7, solid_capstyle="round")
            else:                                             # reference-limited, no boundary claimed
                a2.plot(x, 1.15, "x", color=col, ms=4.2, mew=1.1)
        a2.plot([], [], mk, color=col, ms=4.2, label=f"primary, {nm}")
    a2.axhline(1.5, color="#bbbbbb", lw=0.5)
    a2.text(0.02, 1.15, "no value:", transform=mtr.blended_transform_factory(a2.transAxes, a2.transData), ha="left", va="center", fontsize=6.5, color="#555555")
    a2.plot(mm, 0.1095 / mm, "--", color=THEORY, lw=0.8, label=r"$S^\star_{\rm MSE}$ law (for comparison)")
    a2.plot([], [], "o", color=GREY, ms=4.2, label="filled: boundary resolved")
    a2.plot([], [], "o", color=GREY, mfc="white", ms=4.2, label="hollow: conditional (reference-limited passes)")
    a2.plot([], [], "-", color=GREY, lw=2.2, alpha=0.7, label="bar: inconclusive, bracket (resolved end)")
    a2.plot([], [], ls=(0, (1.2, 1.2)), color=GREY, lw=1.6, label="dotted bar: bracket, reference-limited end")
    a2.plot([], [], "x", color=GREY, ms=4.2, mew=1.1, label="x: reference-limited, no value")
    a2.set_ylim(0.95, 3000); a2.set_ylabel(r"boundary $S^\star$ (symbols per step)")
    a2.set_xscale("log"); a2.set_yscale("log"); a2.set_xlabel(r"step size $\mu$"); a2.set_title(r"BER boundary $S^\star_{\rm BER}$ ($f=2$)")
    st.leg_below(a2, ncol=2); st.panel(a2, "b")
    f.tight_layout(w_pad=1.0); st.save(f, "boundaries")


# ------------------------------------------------------------------ optimum step size and its exponent (P4 + model)
CASES = (("primary_16", PRIMARY, "o", True, "primary 16 dB"), ("primary_14", PRIMARY, "o", False, "primary 14 dB"),
         ("control_16", CONTROL, "s", True, "control 16 dB"), ("control_14", CONTROL, "s", False, "control 14 dB"))
@fig
def muopt():
    SM = json.load(open("results/model/mu_opt_summary.json"))
    f, (a1, a2) = plt.subplots(1, 2, figsize=(st.TXT_W, 2.45), gridspec_kw=dict(width_ratios=[1.25, 1]))
    for tag, col, mk, fill, nm in CASES:
        d = an(tag); used = SM[f"{tag}|theory"]["used"]
        mo = [m for m in d["mu_opt"] if m["S"] in used]
        x = np.array([1.0 / m["S"] for m in mo]); y = np.array([2.0 ** m["log2mu_refined"] for m in mo])
        a1.plot(x, y, mk, color=col, mfc=col if fill else "white", ms=3.6, label=f"{nm} (measured)")
        pts = [p for p in SM[f"{tag}|semi-empirical"]["points"] if p["S"] in used]
        a1.plot([1.0 / p["S"] for p in pts], [2.0 ** p["log2mu"] for p in pts], "-" if fill else ":", color=col, lw=1.0)
    xx = np.array([1 / 2000, 1 / 10]); y0 = 2.0 ** -10.15
    for q, ls, nm in ((0.5, (0, (1, 1.5)), "slope 1/2 (random walk)"), (2 / 3, (0, (4, 2)), "slope 2/3 (steady ramp)")):
        a1.plot(xx, y0 * (xx / xx[0]) ** q, ls=ls, color=THEORY, lw=0.8, label=nm)
    a1.plot([], [], "-", color=GREY, lw=1.0, label="model (lines)")
    a1.set_xscale("log"); a1.set_yscale("log", base=2); a1.set_xlabel(r"variation rate $1/S$ (steps per symbol)"); a1.set_ylabel(r"optimum step size $\mu_{\rm opt}$")
    st.leg_below(a1, ncol=2); st.panel(a1, "a")
    labels = ["primary\n16 dB", "primary\n14 dB", "control\n16 dB", "control\n14 dB"]
    xs = np.arange(4); w = 0.26
    meas = [an(t)["exponent"]["variants"]["V0 baseline (3-pt parabola, bracketed, rho<=0.75)"][0] for t, *_ in CASES]
    sp = [an(t)["exponent"]["variants"]["spread"] for t, *_ in CASES]
    semi = [SM[f"{t}|semi-empirical"]["exp_model"] for t, *_ in CASES]; pure = [SM[f"{t}|theory"]["exp_model"] for t, *_ in CASES]
    err = np.array([[m - s[0] for m, s in zip(meas, sp)], [s[1] - m for m, s in zip(meas, sp)]])
    a2.bar(xs - w, meas, w * 0.92, color="#2a78d6", label="measured (bar: 7 fit variants)", yerr=err, error_kw=dict(lw=0.7, capsize=1.6, ecolor="#333333"))
    a2.bar(xs, semi, w * 0.92, color="#1baf7a", label="model, measured static level")
    a2.bar(xs + w, pure, w * 0.92, color="#eda100", label="model, pure theory")
    for v, ls, t in ((0.5, (0, (1, 1.5)), "1/2"), (2 / 3, (0, (4, 2)), "2/3")):
        a2.axhline(v, color=THEORY, ls=ls, lw=0.8); a2.text(3.7, v + 0.004, t, va="bottom", ha="right", fontsize=6.5)
    a2.set_xticks(xs); a2.set_xticklabels(labels, fontsize=6.5); a2.set_ylim(0.4, 0.72); a2.set_xlim(-0.55, 3.75)
    a2.set_ylabel(r"exponent of $\mu_{\rm opt}\propto(1/S)^{p}$"); a2.grid(axis="x", visible=False)
    st.leg_below(a2, ncol=1, dy=-0.36); st.panel(a2, "b")
    f.tight_layout(w_pad=1.2); st.save(f, "muopt")

@fig
def model():
    E = json.load(open("results/model/explain.json"))
    f, (a1, a2) = plt.subplots(1, 2, figsize=(st.TXT_W, 2.35))
    for tag, col, mk, fill, nm in CASES:
        b = json.load(open(f"results/model/{tag}.json"))["boundary"]
        mus = sorted(float(k) for k in b); g = lambda v: np.nan if v in (None, "undef") else v
        a1.plot(mus, [g(b[[k for k in b if abs(float(k) - m) < 1e-15][0]][0]) for m in mus], mk, color=col, mfc=col if fill else "white", ms=3.6, label=f"{nm}")
        a1.plot(mus, [g(b[[k for k in b if abs(float(k) - m) < 1e-15][0]][1]) for m in mus], "-" if fill else ":", color=col, lw=1.0)
    mm = np.array(MU_FLOAT); a1.plot(mm, 0.1095 / mm, "--", color=THEORY, lw=0.7, label=r"$S^{\star}=0.1095/\mu$")
    a1.plot([], [], "-", color=GREY, label="theory model (lines)")
    a1.set_xscale("log"); a1.set_yscale("log"); a1.set_xlabel(r"step size $\mu$"); a1.set_ylabel(r"$S^\star_{\rm MSE}$")
    a1.set_title("boundary: measured (markers) and model (lines)"); st.leg_below(a1, ncol=2); st.panel(a1, "a")
    for tag, col in (("primary_16", PRIMARY), ("control_16", CONTROL)):
        G = np.array(E[tag]["Gx"])
        a2.plot(G[:, 0], G[:, 1], "-o", color=col, ms=2.6, label=f"{tag.split('_')[0]}: mean-weight model")
        a2.plot(G[:, 0], G[:, 2], ":", color=col, lw=1.0, label=f"{tag.split('_')[0]}: steady ramp $K/x^2$")
    a2.set_xscale("log"); a2.set_yscale("log"); a2.set_xlabel(r"$x=\mu S$"); a2.set_ylabel(r"lag excess MSE $/\,J_{\rm or}$")
    a2.set_title(r"lag depends on $\mu S$ only; flatter than the ramp law"); st.leg_below(a2, ncol=2); st.panel(a2, "b")
    f.tight_layout(w_pad=1.2); st.save(f, "model")


# ------------------------------------------------------------------ abrupt transitions (P2)
STEPS = (("large_up (c 40->116, a 0.31->0.91)", r"$c=40\rightarrow116$ (harsh step up)", 40, 116),
         ("mid_up (c 40->77, a 0.31->0.60)", r"$c=40\rightarrow77$", 40, 77),
         ("down (c 116->40, a 0.91->0.31)", r"$c=116\rightarrow40$ (step down)", 116, 40))
@fig
def p2():
    d = json.load(open("results/p2_final_NT120k_16dB_results.json")); P = d["params"]; NC = P["N_T"] + P["N_PRE"]
    MUS = [2.0 ** -7, 2.0 ** -8, 2.0 ** -9, 2.0 ** -10]
    greens = [plt.get_cmap("Greens")(v) for v in (0.95, 0.75, 0.55, 0.38)]
    f, axs = plt.subplots(1, 3, figsize=(st.TXT_W, 2.05), sharey=True)
    for i, (key, ttl, ca, cb) in enumerate(STEPS):
        ax = axs[i]; ser = d["mse_series64"][key]
        t = (np.arange(len(ser[str(MUS[0])]["R3"])) * 64 + 32 - NC) / 1000.0
        sel = (t > -2) & (t < 16)
        ax.plot(t[sel], np.array(ser[str(MUS[1])]["R2"])[sel], color=R2, lw=1.1, label=r"R2 frozen ($\mu=2^{-8}$)")
        for mu, col in zip(MUS, greens):
            ax.plot(t[sel], np.array(ser[str(mu)]["R3"])[sel], color=col, lw=0.9, label=r"R3 adaptive, $\mu=$" + st.mu_label(mu))
        ja = d["static_reference"][f"{ca}_{MUS[0]}"]["J_min"]; jb = d["static_reference"][f"{cb}_{MUS[0]}"]["J_min"]
        ax.plot([-2, 0], [ja, ja], "--", color=THEORY, lw=0.8); ax.plot([0, 16], [jb, jb], "--", color=THEORY, lw=0.8, label="oracle minimum")
        ax.set_yscale("log"); ax.set_xlim(-2, 16); ax.set_ylim(8e-3, 1.2); ax.set_title(ttl)
        ax.set_xlabel(r"symbols after the step, $(n-N_C)/1000$"); st.panel(ax, "abc"[i])
        if i == 0: ax.set_ylabel("MSE (mean of 100 seeds)")
    h, l = st.collect(axs); st.leg_top(f, h, l, ncol=3, fs=6.5)
    f.tight_layout(w_pad=0.8); st.save(f, "p2")

@fig
def p2nrec():
    d = json.load(open("results/p2_final_NT120k_16dB_results.json"))
    MUS = [2.0 ** -7, 2.0 ** -8, 2.0 ** -9, 2.0 ** -10]
    f, ax = plt.subplots(figsize=(st.COL_W, 2.0)); cols = ["#e34948", "#eda100", "#6250d6"]; mk = ["o", "s", "^"]
    for (key, ttl, ca, cb), col, m in zip(STEPS, cols, mk):
        r = d["steps"][key]; x = np.array(MUS)
        y = np.array([r[str(u)]["N_rec"] for u in MUS]); lo = np.array([r[str(u)]["N_rec_lo"] for u in MUS]); hi = np.array([r[str(u)]["N_rec_hi"] for u in MUS])
        pr = np.array([r[str(u)]["N_rec_pred"] for u in MUS])
        ax.errorbar(x, y, yerr=[np.maximum(y - lo, 0), np.maximum(hi - y, 0)], fmt=m, color=col, ms=3.6, lw=0.7, capsize=1.8,
                    label=fr"$c={ca}\rightarrow{cb}$ (slope {d['slopes'][key]['measured']:.2f})")
        ax.plot(x, pr, "--", color=col, lw=0.9)
    ax.plot([], [], "--", color=GREY, label="mean-weight model")
    ax.set_xscale("log", base=2); ax.set_yscale("log"); ax.set_ylim(250, 6e4); ax.set_xlabel(r"step size $\mu$"); ax.set_ylabel(r"$N_{\rm rec}$ (symbols)")
    st.leg_below(ax, ncol=2, dy=-0.3); f.tight_layout(); st.save(f, "p2nrec")


# ------------------------------------------------------------------ P1: validation and the misadjustment correction
@fig
def p1():
    from scipy.stats import norm
    v = json.load(open("results/v2_revised.json"))["original_data"]["rows"]
    p = json.load(open("results/p1_results.json"))["V2b"]; m = json.load(open("results/misadjustment_investigation.json"))
    f, axs = plt.subplots(1, 4, figsize=(st.TXT_W, 2.05), gridspec_kw=dict(width_ratios=[1, 1, 1, 0.9]))
    a = axs[0]; x = np.linspace(0, 8.5, 100)
    a.plot(x, norm.sf(np.sqrt(2 * 10 ** (x / 10))), color=THEORY, lw=0.9, label=r"$Q(\sqrt{2E_b/N_0})$")
    e = np.array([r["ebn0"] for r in v]); b = np.array([r["ber"] for r in v]); lo = np.array([r["lo_fw"] for r in v]); hi = np.array([r["hi_fw"] for r in v])
    a.errorbar(e, b, yerr=[b - lo, hi - b], fmt="o", color=R1, ms=2.8, lw=0.6, label="R1, flat channel")
    a.set_yscale("log"); a.set_xlabel(r"$E_b/N_0$ (dB)"); a.set_ylabel("BER"); a.set_title("flat channel"); st.leg_below(a, ncol=1, dy=-0.3); st.panel(a, "a")
    a = axs[1]
    for (key, ls, nm) in (("primary a = 0.91", "-", "0.91"), ("control a = 0.60", ":", "0.60")):
        q = p[key]; e = np.array(q["ebn0"])
        a.plot(e, q["R1_exact"], ls, color=THEORY, lw=0.7)
        for rx in ("R1", "R2", "R3"):
            y = np.array(q[rx]); z = y <= 3.01e-6
            a.plot(e[~z], y[~z], ls, marker="o", color=RX[rx], ms=2.6, lw=1.0, label=f"{RXNAME[rx]}" if nm == "0.91" else None)
            if z.any(): a.plot(e[z], y[z], "v", color=RX[rx], mfc="white", ms=3.2)
    a.plot([], [], "-", color=GREY, label=r"$a=0.91$"); a.plot([], [], ":", color=GREY, label=r"$a=0.60$")
    a.set_yscale("log"); a.set_ylim(4e-7, 0.5); a.set_xlabel(r"$E_b/N_0$ (dB)"); a.set_title("static ISI channels"); st.leg_below(a, ncol=2, dy=-0.3); st.panel(a, "b")
    a = axs[2]; sw = m["sweep"]
    s_ = np.array([r["s"] for r in sw]); r_ = np.array([r["meas_over_tb"] for r in sw]); ci = np.array([r["meas_over_tb_ci"] for r in sw]); ex = np.array([r["exact_over_tb"] for r in sw])
    a.axhline(1, color=THEORY, lw=0.8, ls="--", label="textbook $\\mu\\,\\mathrm{tr}(\\mathbf{R})J_{\\min}/2$")
    a.plot(s_, ex, "-", color="#1baf7a", lw=1.2, label="correlated-error model (9)")
    a.errorbar(s_, r_, yerr=ci, fmt="o", color=R3, ms=2.8, lw=0.6, label="measured, $\\mu=2^{-9}$")
    a.set_xlabel(r"ISI strength $s$ ($h=[1,0.6s,0.1s]$)"); a.set_ylabel("excess MSE / textbook"); a.set_title("misadjustment"); st.leg_below(a, ncol=1, dy=-0.3); st.panel(a, "c")
    a = axs[3]; lag = np.arange(1, 6)
    a.bar(lag - 0.18, m["table"]["acf"][1:6], 0.34, color=PRIMARY, label=r"ISI channel ($a=0.60$)")
    a.bar(lag + 0.18, m["flat"]["acf"][1:6], 0.34, color=GREY, label="flat channel")
    a.axhline(0, color="#444444", lw=0.6); a.set_xlabel("lag $j$"); a.set_ylabel("autocorrelation of $e_o[n]$"); a.set_title("residual Wiener error"); st.leg_below(a, ncol=1, dy=-0.3); a.grid(axis="x", visible=False)
    st.panel(a, "d")
    f.tight_layout(w_pad=0.5); st.save(f, "p1")

@fig
def delay():
    c = json.load(open("results/commit/c2.json"))["a"]
    f, a = plt.subplots(figsize=(st.COL_W, 1.9))
    for key, col, nm in (("nmp [0.5, 1.0]", R1, r"$h=[0.5,\,1.0]$ (non-min. phase)"), ("mp [1.0, 0.5]", R2, r"$h=[1.0,\,0.5]$ (mirror)")):
        q = c[key]; a.plot(q["Delta"], q["J_oracle"], "-", color=col, lw=1.2, label=nm + ", Wiener")
        a.plot(q["Delta"], q["J_lms"], "o", color=col, mfc="white", ms=3, label="LMS (measured)" if key.startswith("nmp") else None)
    a.set_yscale("log"); a.set_xlabel(r"decision delay $\Delta$"); a.set_ylabel("MSE"); st.leg_below(a, ncol=1, dy=-0.3)
    from matplotlib.ticker import LogLocator, NullFormatter
    a.yaxis.set_minor_formatter(NullFormatter()); a.set_xticks(range(0, 17, 2))
    f.tight_layout(); st.save(f, "delay")


# ------------------------------------------------------------------ P5 audio (supervised LMS)
@fig
def audio():
    from scipy.io import wavfile
    from lms_lib import triangle_counter
    m = json.load(open("results/p5/p5_metrics.json"))
    fs, o = wavfile.read("results/p5/original_8k.wav"); o = o.astype(np.uint8); nb = 8 * len(o); T = nb / 8 / fs
    SC = (("static", None, "static"), ("slow_S1000", 1000, r"$S=1000$"), ("boundary_S28", 28, r"$S=28=S^\star_{\rm MSE}$"), ("fast_S1", 1, r"$S=1$"))
    f = plt.figure(figsize=(st.TXT_W, 2.9))
    gs = f.add_gridspec(5, 2, width_ratios=[2.15, 1], height_ratios=[1.05, 1, 1, 1, 1], hspace=0.18, wspace=0.16)
    a0 = f.add_subplot(gs[0, 0]); t = np.arange(len(o)) / fs
    a0.plot(t, o.astype(float) - 128, color="#555555", lw=0.25); a0.set_xlim(0, T); plt.setp(a0.get_xticklabels(), visible=False); a0.set_yticks([]); a0.set_ylabel("voice", fontsize=6.5)
    a0.grid(False); a0.spines["left"].set_visible(False); st.panel(a0, "a", x=-0.01)
    for i, (sc, S, lab) in enumerate(SC):
        a = f.add_subplot(gs[i + 1, 0], sharex=a0)
        if S is not None:
            c = triangle_counter(30000 + nb, 30000, 40, 116, S)[30000:30000 + nb] / 128.0
            tt = np.arange(nb) / 8 / fs; step = max(1, nb // 40000)
            if S >= 200: a.plot(tt[::step], (c[::step] - 0.3125) / (0.90625 - 0.3125) * 3.0 + 0.0, color="#bbbbbb", lw=0.6, zorder=0)
            else: a.axhspan(0, 3, color="#eeeeee", lw=0, zorder=0)
        for j, rx in enumerate(("R1", "R2", "R3")):
            _, y = wavfile.read(f"results/p5/{sc}_{rx}.wav"); x = np.bitwise_xor(o, y.astype(np.uint8))
            idx = np.nonzero(np.unpackbits(x))[0] / 8 / fs
            a.vlines(idx, j + 0.15, j + 0.85, color=RX[rx], lw=0.35, alpha=0.9)
        a.set_ylim(0, 3); a.set_yticks([0.5, 1.5, 2.5]); a.set_yticklabels(["R1", "R2", "R3"], fontsize=5.5); a.grid(False)
        a.set_ylabel(lab, fontsize=6, rotation=0, ha="right", va="center", labelpad=2)
        if i < 3: plt.setp(a.get_xticklabels(), visible=False)
        else: a.set_xlabel("time in the recording (s)")
    b = f.add_subplot(gs[:, 1]); xs = np.arange(4); w = 0.27
    for j, rx in enumerate(("R1", "R2", "R3")):
        ber = np.array([m["metrics"][sc][rx]["BER"] for sc, _, _ in SC]); n = np.array([m["metrics"][sc][rx]["bit_errors"] for sc, _, _ in SC])
        y = np.where(n > 0, ber, np.nan)
        b.bar(xs + (j - 1) * w, y, w * 0.9, color=RX[rx], label=RXNAME[rx])
        for k in np.nonzero(n == 0)[0]: b.text(xs[k] + (j - 1) * w, 2e-7, "0", ha="center", fontsize=6, color=RX[rx])
    for k, (sc, _, _) in enumerate(SC):
        snr = m["metrics"][sc]["R3"]["waveform_SNR_dB"]
        b.text(xs[k] + w, m["metrics"][sc]["R3"]["BER"] * 2.2, f"{snr:.0f} dB", ha="center", fontsize=5.6, color=R3, rotation=90, va="bottom")
    b.set_yscale("log"); b.set_ylim(1.5e-7, 0.2); b.set_xticks(xs); b.set_xticklabels(["static", "1000", "28", "1"], fontsize=6.5)
    b.set_xlabel(r"variation rate $S$"); b.set_ylabel("BER"); b.yaxis.set_label_position("right"); b.yaxis.tick_right()
    b.spines["right"].set_visible(True); b.spines["left"].set_visible(False); b.grid(axis="x", visible=False)
    st.leg_below(b, ncol=1, dy=-0.13); st.panel(b, "b", x=0.02)
    b.set_title("BER; R3 label = waveform SNR", fontsize=7)
    st.save(f, "audio")

# ------------------------------------------------------------------ image payload
@fig
def image_stats():
    c = json.load(open("results/commit/c10b.json"))
    f, (a1, a2) = plt.subplots(1, 2, figsize=(st.TXT_W, 2.1), gridspec_kw=dict(width_ratios=[1, 1.35]))
    band = np.arange(1, 10)
    for snr, ls in (("12.0", "-"), ("10.0", "--"), ("8.0", ":")):
        q = c[f"{snr}|S=1000 (one ramp over the image)"]
        for rx in ("R2", "R3"):
            y = np.array(q[rx]["band"], float); y[y == 0] = np.nan
            a1.plot(band, y, ls, marker="o", ms=2.4, color=RX[rx], lw=1.1, label=f"{rx}, {snr[:-2]} dB")
    a1.set_yscale("log"); a1.set_xlabel("band of 8 image rows (top $\\rightarrow$ bottom)"); a1.set_ylabel("BER in the band")
    a1.set_title(r"$S=1000$: channel ramps once over the image"); a1.set_ylim(1.5e-5, 0.3); st.leg_below(a1, ncol=3); st.panel(a1, "a")
    keys = [("static", "static"), ("S=1000 (one ramp over the image)", "1000"), ("S=112", "112"), ("S=28 (S*_MSE)", "28"), ("S=5", "5"), ("S=1", "1"), ("S=1, mu=2^-5", "1\n$\\mu=2^{-5}$")]
    xs = np.arange(len(keys)); w = 0.27
    for j, rx in enumerate(("R1", "R2", "R3")):
        y = np.array([c[f"10.0|{k}"][rx]["bad_pix"] for k, _ in keys], float)
        a2.bar(xs + (j - 1) * w, np.where(y > 0, y, np.nan), w * 0.9, color=RX[rx], label=RXNAME[rx])
    a2.set_yscale("log"); a2.set_xticks(xs); a2.set_xticklabels([l for _, l in keys], fontsize=6.3); a2.set_xlabel(r"variation rate $S$ ($\mu=2^{-8}$ unless stated)")
    a2.set_ylabel("wrong pixels (of 9216)"); a2.set_title("10 dB, 5-seed mean")
    a2.grid(axis="x", visible=False); st.leg_below(a2, ncol=3, dy=-0.42); st.panel(a2, "b")
    f.tight_layout(w_pad=1.0); st.save(f, "image_stats")


# ------------------------------------------------------------------ P6: word length against the boundary (L2)
@fig
def fxp():
    P = list(range(5, 12)); BA = [(26, 12), (16, 12), (14, 12), (12, 12), (10, 10)]
    def get(fam, key):
        out = []
        for p in P:
            r = json.load(open(f"results/p6c/surface_{fam}_{p}.json")).get(key)
            out.append(None if (r is None or "u" in r["status"] or r["S_star"] is None) else r["S_star"])
        return out
    f, axs = plt.subplots(1, 3, figsize=(st.TXT_W, 2.45), gridspec_kw=dict(width_ratios=[1, 1, 0.8]))
    cm = plt.get_cmap("Oranges")
    for ax, rnd, ttl, lt in ((axs[0], 1, "round to nearest", "a"), (axs[1], 0, "truncation", "b")):
        ref = get("A", f"26|12|{rnd}")
        M = np.full((len(BA), len(P)), np.nan); T = [[""] * len(P) for _ in BA]
        for i, (ba, bm) in enumerate(BA):
            row = get("A", f"{ba}|{bm}|{rnd}")
            for j, v in enumerate(row):
                if v is None: T[i][j] = "fails"
                else: M[i, j] = np.log2(v / ref[j]); T[i][j] = str(v)
        ax.imshow(np.zeros_like(M), cmap="Greys", vmin=0, vmax=1, aspect="auto")
        im = ax.imshow(np.where(np.isnan(M), np.nan, M), cmap=cm, vmin=-0.3, vmax=3.2, aspect="auto")
        for i in range(len(BA)):
            for j in range(len(P)):
                if np.isnan(M[i, j]):
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor="#d9d9d9", hatch="////", edgecolor="white", lw=0.0))
                    ax.text(j, i, "fails", ha="center", va="center", fontsize=5.2, color="#444444")
                else:
                    ax.text(j, i, T[i][j], ha="center", va="center", fontsize=6.2, color="white" if M[i, j] > 1.6 else "#222222")
        ax.set_xticks(range(len(P))); ax.set_xticklabels([r"$2^{-%d}$" % p for p in P], fontsize=6.5)
        ax.set_yticks(range(len(BA))); ax.set_yticklabels([f"{ba}" if bm == 12 else f"{ba} ({bm})" for ba, bm in BA], fontsize=6.5)
        ax.set_xlabel(r"step size $\mu$"); ax.set_title(ttl); ax.grid(False)
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.tick_params(length=0)
        if rnd: ax.set_ylabel(r"accumulator width $B_{\rm acc}$")
        st.panel(ax, lt)
    a = axs[2]; mu = 2.0 ** -np.array(P)
    for bm, col, mk in ((16, "#1baf7a", "o"), (12, PRIMARY, "s"), (8, "#eb6834", "^")):
        for rr, fill in ((1, True), (0, False)):
            y = [np.nan if v is None else v for v in get("B", f"26|{bm}|{rr}")]
            a.plot(mu, y, "-" if rr else ":", marker=mk, color=col, mfc=col if fill else "white", ms=3.4, lw=0.9,
                   label=fr"$B_{{\rm mul}}={bm}$" if rr else None)
    a.plot([], [], "-", color=GREY, label="rounding"); a.plot([], [], ":", color=GREY, label="truncation")
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel(r"step size $\mu$"); a.set_ylabel(r"$S^\star_{\rm MSE}$")
    a.set_title(r"multiplier width ($B_{\rm acc}=26$)"); st.leg_below(a, ncol=2); st.panel(a, "c")
    f.tight_layout(w_pad=0.8)
    p0 = axs[0].get_position(); p1 = axs[1].get_position()
    cax = f.add_axes([p0.x0 + 0.05, p0.y0 - 0.27, p1.x1 - p0.x0 - 0.1, 0.035]); cb = f.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_ticks([0, 1, 2, 3]); cb.set_ticklabels([r"same as 26 bit", r"$2\times$ slower", r"$4\times$", r"$8\times$"]); cb.outline.set_linewidth(0.4)
    cb.ax.tick_params(labelsize=6.8); cb.set_label("shading: how far the boundary moves to slower variation", fontsize=7)
    st.save(f, "fxp")


# ------------------------------------------------------------------ replications
@fig
def replication():
    import os
    here = os.getcwd(); sys.path.insert(0, os.path.join(here, "replication")); os.chdir("replication")
    from scipy.stats import norm
    from matplotlib.ticker import NullFormatter
    VA, VB, VC = "#6250d6", "#eda100", "#1baf7a"
    import rep2_mathworks as r2, rep4_shahdoosti as r4, rep5_ghanassi as r5, rep6_tracking_theory as r6
    f, axg = plt.subplots(2, 3, figsize=(st.TXT_W, 4.3)); axs = [axg[0, 0], axg[0, 1], axg[0, 2], axg[1, 0], axg[1, 1], axg[1, 2]]
    a = axs[0]; d = np.load("results/rep1_bpsk.npy"); x = np.linspace(0, 10.5, 200)
    a.plot(x, norm.sf(np.sqrt(2 * 10 ** (x / 10))), color=THEORY, lw=0.9, label="Gaussian theory")
    a.plot(d[:, 0], d[:, 3], "o", color=VA, ms=2.6, label="sim., Gaussian")
    a.plot(d[:, 0], d[:, 5], "--", color=VB, lw=0.9, label="exact, 12 uniforms")
    a.plot(d[:, 0], np.where(d[:, 7] >= 10, d[:, 6], np.nan), "s", color=VB, mfc="white", ms=2.6, label="sim., LFSR noise")
    a.set_yscale("log"); a.set_ylim(1e-7, 0.2); a.set_xlabel(r"$E_b/N_0$ (dB)"); a.set_ylabel("BER"); a.set_title("R1 BPSK"); st.leg_below(a, ncol=1, dy=-0.33, fs=5.8); st.panel(a, "a")
    a = axs[1]; rng = np.random.default_rng(2718)
    E = np.array([r2.run_once(rng, "zeros", want_err=True) for _ in range(500)])
    a.plot(E.mean(0), color=VC, lw=1.0, label="mean $|e|$, 500 runs"); a.axvline(200, color=GREY, ls="--", lw=0.8, label="end of training")
    a.axhline(0.1, color=THEORY, ls=":", lw=0.8); a.set_xlim(0, 600); a.set_xlabel("symbol"); a.set_ylabel("$|e|$"); a.set_title("R2 MathWorks"); st.leg_below(a, ncol=1, dy=-0.33, fs=5.8); st.panel(a, "b")
    a = axs[2]; logf, _, _ = r4.run(False); logq, first, _ = r4.run(True)
    a.plot([abs(l[1]) for l in logf], color=GREY, lw=0.8, label="floating point"); a.plot([abs(l[1]) for l in logq], color=VA, lw=0.9, label="12 frac. bits")
    a.axhline(r4.LSB / (2 * r4.mu * 0.5), color=THEORY, ls=":", lw=0.8); a.axvline(first, color=VB, ls="--", lw=0.8, label=f"stall from {first}")
    a.set_yscale("log"); a.set_xlim(0, 400); a.set_ylim(1e-5, 1); a.set_xlabel("iteration"); a.set_ylabel("$|e|$"); a.set_title("R4 stall onset"); st.leg_below(a, ncol=1, dy=-0.33, fs=5.8); st.panel(a, "c")
    a = axs[3]; d5 = np.load("results/rep5d_vs_paper.npy"); import rep5c_ghanassi_fulltext as r5c
    for acc, col, mk, nm in ((0, VA, "o", "ours, products rounded"), (1, VC, "s", "ours, wide accumulator")):
        m = d5[d5[:, 0] == acc]
        a.plot(m[:, 1], m[:, 2], "x", color=THEORY if acc == 0 else GREY, ms=3.6, mew=0.9, label="paper's simulation (digitised)" if acc == 0 else None)
        a.plot(m[:, 1], m[:, 3], mk, color=col, ms=2.8, mfc="white" if acc else col, label=nm)
    fine = np.geomspace(0.001, 0.18, 300); F = np.array([r5c.formulas(u, False) for u in fine])
    a.plot(fine, F[:, 0], "--", color=THEORY, lw=0.7, label="paper's stall formula (Eq. 11)")
    a.set_xscale("log"); a.set_yscale("log"); a.set_ylim(1e-9, 3e-5); a.set_xlim(8e-4, 0.17); a.set_xlabel(r"$\mu$"); a.set_ylabel("steady-state sq. error")
    a.set_title("R5 fixed point (full text)"); st.leg_below(a, ncol=1, dy=-0.33, fs=5.8); st.panel(a, "d")
    a = axs[4]; res = np.load("results/rep6_curves.npy", allow_pickle=True).item(); xis = np.array([0.0002, 0.0005, 0.001, 0.002, 0.004, 0.008])
    ms0 = [r6.refine_min(*res[str((0, float(x)))][:2])[0] for x in xis]; ms1 = [r6.refine_min(*res[str((1, float(x)))][:2])[0] for x in xis]
    th0 = xis / np.sqrt(r6.SV2 * r6.N); th1 = (4 * xis ** 2 / (r6.N * r6.SV2)) ** (1 / 3)
    a.plot(xis, ms0, "o", color=VA, ms=2.6, label="random walk"); a.plot(xis, th0, "-", color=VA, lw=0.8)
    a.plot(xis, ms1, "s", color=VB, ms=2.6, label="ramp"); a.plot(xis, th1, "-", color=VB, lw=0.8)
    a.plot([], [], "-", color=GREY, lw=0.8, label="theory (10)/(11)")
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel(r"variation $\xi$"); a.set_ylabel(r"$\mu_{\rm opt}$"); a.set_title("R6 tracking"); st.leg_below(a, ncol=1, dy=-0.33, fs=5.8); a.xaxis.set_minor_formatter(NullFormatter()); st.panel(a, "e")
    a = axs[5]; r7 = np.load("results/rep7_bergmans.npy", allow_pickle=True).item()
    for b, col, mk in ((0.1, VA, "s"), (0.01, VB, "^")):
        v = r7[("Fig. 4", b)]
        a.plot(v["mu"], 10 * np.log10(v["sim"]), mk, color=col, ms=2.6, mfc="white", label=rf"sim., $\beta={b}$")
        a.plot(v["mu"], 10 * np.log10(v["th"]), "-", color=col, lw=0.8)
    a.plot([], [], "-", color=GREY, lw=0.8, label="paper's theory (10)+(27)")
    a.set_xscale("log", base=2); a.set_ylim(-9, 6); a.set_xlabel(r"$\mu$"); a.set_ylabel(r"$\varepsilon/N_0$ (dB)"); a.set_title("R7 gain variation (Fig. 4)")
    st.leg_below(a, ncol=1, dy=-0.33, fs=5.8); st.panel(a, "f")
    os.chdir(here); f.tight_layout(w_pad=1.0, h_pad=1.2); st.save(f, "replication")

@fig
def scorecard():
    # measured / published (or theory) value; ranges are min-max over the stated conditions (values from replication/results/*log*.txt)
    items = [  # label, lo, hi, verdict
        ("R1  BPSK BER / theory, 0-8 dB", 1.000, 1.002, "rep"),
        ("R1  LFSR-noise BER / exact Irwin-Hall, 0-9 dB", 0.998, 1.056, "rep"),
        ("R2  convergence: median 108 / stated 200 symbols", 108 / 200, 108 / 200, "bound"),
        ("R2  in MATLAB: median 115 / stated 200 symbols", 115 / 200, 115 / 200, "bound"),
        ("R2  our LMS in MATLAB: MSE / Python MSE", 0.9882, 0.9991, "rep"),
        ("R3  LMS coefficients / Wiener solution", 1.0017, 1.0018, "rep"),
        ("R3  misadjustment / formula, white input", 1.013, 1.030, "rep"),
        ("R3  misadjustment / formula, ISI channel", 1.468, 1.480, "mis"),
        ("R4  stall onset iteration (134 / 134)", 1.0, 1.0, "rep"),
        (r"R5  our sim. / paper's sim., no accumulator, $\mu\leq0.155$", 0.85, 1.19, "rep"),
        (r"R5  our sim. / paper's sim., wide accumulator, $\mu\leq0.155$", 0.72, 1.19, "rep"),
        (r"R5  wide accumulator, at the error minimum ($\mu$ = 0.063-0.084)", 1.65, 2.34, "part"),
        (r"R6  $\mu_{\rm opt}$ / theory, random walk", 0.911, 0.992, "rep"),
        (r"R6  $\mu_{\rm opt}$ / refined theory, ramp", 0.989, 1.024, "rep"),
        ("R6  exponent / theory (1.000; 0.599 vs 0.605)", 0.990, 1.000, "rep"),
        (r"R7  excess error / paper's theory, 6 curves, $\pm0.37$ dB", 10 ** (-0.18 / 10), 10 ** (0.37 / 10), "rep")]
    col = {"rep": R3, "part": "#eda100", "mis": "#e34948", "bound": R2}
    nm = {"rep": "reproduced", "part": "partly reproduced", "mis": "documented mismatch (explained)", "bound": "bound satisfied"}
    f, a = plt.subplots(figsize=(5.4, 3.35))
    a.axvspan(0.9, 1.1, color="#eef3ea", lw=0); a.axvline(1, color=THEORY, lw=0.6)
    y = np.arange(len(items))[::-1]
    for yy, (lab, lo, hi, v) in zip(y, items):
        if hi > lo: a.plot([lo, hi], [yy, yy], "-", color=col[v], lw=3.2, solid_capstyle="round", alpha=0.85)
        a.plot(np.sqrt(lo * hi), yy, "D" if v == "bound" else "o", color=col[v], ms=3.6, mec="white", mew=0.5)
    a.set_yticks(y); a.set_yticklabels([i[0] for i in items], fontsize=6.8); a.set_xscale("log")
    a.set_xticks([0.5, 0.7, 1, 1.5, 2]); a.set_xticklabels(["0.5", "0.7", "1", "1.5", "2"]); a.set_xticks([], minor=True); a.set_xlim(0.45, 2.5)
    a.set_xlabel("our value / published or theoretical value"); a.grid(axis="y", visible=False)
    for v in ("rep", "part", "mis", "bound"): a.plot([], [], "-", color=col[v], lw=3, label=nm[v])
    a.legend(fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=4)
    a.text(1.0, len(items) - 0.35, "±10 %", fontsize=5.5, ha="center", color="#557755")
    st.save(f, "scorecard")


# ------------------------------------------------------------------ BER against MSE (existing data only)
@fig
def bermse():
    from scipy.stats import norm
    mus = (2.0 ** -5, 2.0 ** -6, 2.0 ** -7, 2.0 ** -8, 2.0 ** -10, 2.0 ** -11.5)
    cols = st.blues(len(mus))[::-1]
    f, axs = plt.subplots(1, 2, figsize=(st.COL_W, 2.0), sharey=True)
    for i, (ax, tag, snr) in enumerate(zip(axs, ("primary_16", "primary_14"), (16, 14))):
        res = an(tag)["res"]
        for mu, c in zip(mus, cols):
            rows = [r for r in res[mkey(res, mu)]["rows"] if r["E3"] >= 20]   # resolved BER only
            J = np.array([r["J3"] for r in rows]); B = np.array([r["ber3"] for r in rows])
            ax.plot(J, B, "-o", color=c, ms=2.0, lw=0.9, label=r"$\mu=$" + st.mu_label(mu))
        j = np.geomspace(0.015, 0.15, 100)
        ax.plot(j, norm.sf(1 / np.sqrt(j)), "--", color=THEORY, lw=0.9, label=r"Gaussian $Q(1/\sqrt{J})$")
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.018, 0.15); ax.set_ylim(1e-8, 1e-2)
        ax.set_xlabel(r"R3 MSE $J$"); ax.set_title(f"primary, {snr} dB", fontsize=7.5); st.panel(ax, "ab"[i])
        from matplotlib.ticker import NullFormatter; ax.xaxis.set_minor_formatter(NullFormatter()); ax.set_xticks([0.02, 0.05, 0.1]); ax.set_xticklabels(["0.02", "0.05", "0.1"])
    axs[0].set_ylabel("R3 BER")
    h, l = st.collect(axs); f.tight_layout(w_pad=0.6); st.leg_top(f, h, l, ncol=4, fs=5.6)
    st.save(f, "bermse")

# ------------------------------------------------------------------ decision-directed divergence map
@fig
def dd():
    c = json.load(open("results/commit/c5c.json")); P = [5, 6, 7, 8]; SN = [4, 6, 8, 10, 12, 14]
    f, a = plt.subplots(figsize=(st.COL_W, 1.75))
    M = np.array([[c[f"28|{p}|{s:.1f}"]["ber_dd"] / c[f"28|{p}|{s:.1f}"]["ber_sup"] for s in SN] for p in P])
    im = a.imshow(np.log10(M), cmap="Reds", vmin=-0.2, vmax=2.2, aspect="auto")
    for i, p in enumerate(P):
        for j, s_ in enumerate(SN):
            q = c[f"28|{p}|{s_:.1f}"]; r = M[i, j]
            txt = (f"{r:.0f}" if r >= 10 else f"{r:.2f}") + (f"\n{q['bad_seeds']}/20 lost" if q["bad_seeds"] else "")
            a.text(j, i, txt, ha="center", va="center", fontsize=5.4, color="white" if np.log10(r) > 1.2 else "#222222")
    a.set_xticks(range(len(SN))); a.set_xticklabels([f"{s} dB" for s in SN], fontsize=6.5)
    a.set_yticks(range(len(P))); a.set_yticklabels([r"$2^{-%d}$" % p for p in P]); a.set_ylabel(r"step size $\mu$"); a.grid(False)
    for sp in a.spines.values(): sp.set_visible(False)
    a.tick_params(length=0)
    cb = f.colorbar(im, ax=a, fraction=0.05, pad=0.02); cb.set_label("BER ratio DD / supervised", fontsize=6.5)
    cb.set_ticks([0, 1, 2]); cb.set_ticklabels(["1", "10", "100"]); cb.outline.set_linewidth(0.4)
    f.tight_layout(); st.save(f, "dd")

# ------------------------------------------------------------------ triangle against sinusoid
@fig
def trisin():
    c = json.load(open("results/commit/c1.json")); SS = [1000, 320, 112, 56, 28, 14, 5]
    f, a = plt.subplots(figsize=(st.COL_W, 2.2))
    cols = {0.015625: "#08306b", 0.00390625: "#2a78d6", 0.0009765625: "#9ecae1"}
    for mu, col in cols.items():
        for shape, ls, mk in (("triangle", "-", "o"), ("sine", "--", "s"), ("sine_peak", ":", "^")):
            y = [c[f"16.0|{S}|{shape}|{mu}"]["eps3"] for S in SS]
            a.plot(SS, y, ls, marker=mk, color=col, ms=2.6, lw=1.0, mfc="white" if shape != "triangle" else col)
    for mu, col in cols.items(): a.plot([], [], "-", color=col, lw=2, label=r"$\mu=$" + st.mu_label(mu))
    for shape, ls, mk, nm in (("triangle", "-", "o", "triangle"), ("sine", "--", "s", "sinusoid, same average rate"), ("sine_peak", ":", "^", "sinusoid, same peak rate")):
        a.plot([], [], ls, marker=mk, color=GREY, ms=2.6, label=nm)
    a.set_xscale("log"); a.set_yscale("log"); a.invert_xaxis(); a.set_xlabel(r"$S$ (faster $\rightarrow$)"); a.set_ylabel(r"R3 excess MSE $\varepsilon$")
    st.leg_below(a, ncol=2, dy=-0.25, fs=5.9); f.tight_layout(); st.save(f, "trisin")

# ------------------------------------------------------------------ coefficient trajectories
@fig
def traj():
    z = np.load("results/commit/c6_series.npz"); J = json.load(open("results/commit/c6.json"))
    f, axs = plt.subplots(1, 3, figsize=(st.TXT_W, 1.75), sharey=True)
    tc = ["#2a78d6", "#eb6834", "#6250d6"]
    for i, (a, S) in enumerate(zip(axs, (1000, 56, 14))):
        t = z[f"t{S}"]; Wl = z[f"wl{S}"]; Wo = z[f"wo{S}"]; taps = J[str(S)]["moving_taps"]
        for k, col in zip(taps, tc):
            a.plot(t, Wo[:, k], "-", color=col, lw=1.2, label=fr"optimum $w^\star_{{{k}}}$" if i == 0 else None)
            a.plot(t, Wl[:, k], "--", color=col, lw=1.0, label=fr"LMS $w_{{{k}}}$" if i == 0 else None)
        rel = J[str(S)]["rel_rms_coef_error"]
        a.set_title(fr"$S={S}$  (rel. error {rel:.2f})"); a.set_xlabel("time / period"); st.panel(a, "abc"[i])
    axs[0].set_ylabel("coefficient"); h, l = st.collect(axs); st.leg_top(f, h, l, ncol=6, fs=6.3)
    f.tight_layout(w_pad=0.4); st.save(f, "traj")


# ------------------------------------------------------------------ image grid (same run function and seed as c10c_image_fig.py)
@fig
def image_grid():
    import types
    src = open("c10b_image_lowsnr.py").read().split("SEEDS = range")[0]
    mod = types.ModuleType("c10b_defs"); exec(compile(src.replace('log = open(f"{OUT}/c10b_log.txt", "w")', 'log = None'), "c10b_defs", "exec"), mod.__dict__)
    scen = [("static", None, 2.0 ** -8), (r"$S=1000$", 1000, 2.0 ** -8), (r"$S=1$", 1, 2.0 ** -8), (r"$S=1$, $\mu=2^{-5}$", 1, 2.0 ** -5)]
    f, axs = plt.subplots(4, 4, figsize=(st.COL_W, 2.55), gridspec_kw=dict(hspace=0.32, wspace=0.04))
    for i, (name, S, mu) in enumerate(scen):
        o = mod.run(S, 10.0, mu, 700001)
        axs[i, 0].imshow(mod.pix, cmap="gray", vmin=0, vmax=255); axs[i, 0].set_ylabel(name, fontsize=6, rotation=0, ha="right", va="center")
        for j, k in enumerate(("R1", "R2", "R3")):
            axs[i, j + 1].imshow(o[k]["img"], cmap="gray", vmin=0, vmax=255)
            axs[i, j + 1].set_title(f"{k}: {o[k]['bad_pix']} px", fontsize=5.6, color=RX[k], pad=1.5)
        for a in axs[i]:
            a.set_xticks([]); a.set_yticks([]); a.grid(False)
            for sp in a.spines.values(): sp.set_visible(True); sp.set_linewidth(0.3); sp.set_color("#999999")
    axs[0, 0].set_title("original", fontsize=5.6, pad=1.5)
    st.save(f, "image_grid")

if __name__ == "__main__":
    names = sys.argv[1:] or list(FIGS)
    for n in names: FIGS[n]()
