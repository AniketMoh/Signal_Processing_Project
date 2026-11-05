# plot_board.py -- figure of the board sweeps (level L5): BER of R1/R2/R3 and R3 MSE against the variation rate S.
# Reads results/board_sweep_<build>_*.json written by run_board.py.
#   python plot_board.py            -> results/fig_L5_board_tracking.png (screen version, with a title line)
#   python plot_board.py --report   -> ../report/figs/board.pdf (print size for the two-column report; the caption carries the title)
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
BUILD = "m12_a16_r1"                                  # default board build
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
RX = [("R1 direct", "#2a78d6", "s"), ("R2 frozen", "#eb6834", "^"), ("R3 adaptive", "#1baf7a", "o")]
MU = [("6", "#86b6ef", "D"), ("8", "#2a78d6", "o"), ("10", "#184f95", "v")]       # one hue, light -> dark = larger -> smaller mu

SCREEN = dict(size=(15, 4.6), lw=2.0, ms=6, mew=1.5, f_lab=9, f_tit=10, f_ann=8, f_leg=8, f_tick=9, f_note=7, dx=6,
              xlabel="symbols per channel step S (faster variation to the right)",
              titles=("(a) BER, 10 dB, mu = 2^-8 (dotted: static channel)", "(b) R3 BER against step size, 10 dB", "(c) MSE, 10 dB"))
REPORT = dict(size=(7.0, 2.75), lw=1.3, ms=3.2, mew=0.8, f_lab=6.5, f_tit=7, f_ann=5.5, f_leg=5.5, f_tick=6, f_note=5, dx=3,
              xlabel="S, symbols per step (faster to the right)",
              titles=("(a) BER, 10 dB, $\\mu=2^{-8}$", "(b) R3 BER, 10 dB", "(c) MSE, 10 dB"))


def load(eb, p):
    f = os.path.join(RES, f"board_sweep_{BUILD}_{eb}dB_mu2-{p}.json")
    return json.load(open(f)) if os.path.isfile(f) else None


def xy(d, key, i):
    rows = [r for r in d["rows"] if r["S"] is not None]
    xs = [r["S"] for r in rows]
    ys = [max(r[key][i], 1e-7) for r in rows]
    st = [r for r in d["rows"] if r["S"] is None][0][key][i]
    return xs, ys, st


def style(ax, k, title, ylabel):
    ax.set_facecolor(SURF)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.invert_xaxis()
    ax.grid(True, which="major", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=k["f_tick"])
    ax.set_xlabel(k["xlabel"], color=INK2, fontsize=k["f_lab"])
    ax.set_ylabel(ylabel, color=INK2, fontsize=k["f_lab"])
    ax.set_title(title, color=INK, fontsize=k["f_tit"], loc="left")


def line(ax, k, xs, ys, col, mk, label, tag):
    ax.plot(xs, ys, color=col, lw=k["lw"], marker=mk, ms=k["ms"], mec=SURF, mew=k["mew"], label=label)
    ax.annotate(tag, (xs[-1], ys[-1]), xytext=(k["dx"], 0), textcoords="offset points", color=INK, fontsize=k["f_ann"], va="center")


def main():
    report = "--report" in sys.argv
    k = REPORT if report else SCREEN
    base = load(10, 8)
    fig, axs = plt.subplots(1, 3, figsize=k["size"], facecolor=SURF)
    # (a) the three receivers, 10 dB, mu = 2^-8
    ax = axs[0]
    for i, (name, col, mk) in enumerate(RX):
        xs, ys, st = xy(base, "ber", i)
        line(ax, k, xs, ys, col, mk, name, name.split()[0])
        ax.axhline(max(st, 1e-7), color=col, lw=0.8, ls=":", alpha=0.8)
    ax.axhline(1e-4, color=INK2, lw=0.8, ls="--")
    ax.text(5000, 1.2e-4, "validity limit of hardware noise", color=INK2, fontsize=k["f_note"])
    style(ax, k, k["titles"][0], "bit error rate")
    ax.legend(frameon=False, fontsize=k["f_leg"], labelcolor=INK, loc="center left", bbox_to_anchor=(0.0, 0.2))
    # (b) R3 BER for three step sizes
    ax = axs[1]
    for (p, col, mk) in MU:
        d = load(10, p)
        if d:
            xs, ys, _ = xy(d, "ber", 2)
            line(ax, k, xs, ys, col, mk, f"R3, $\\mu=2^{{-{p}}}$", f"$2^{{-{p}}}$")
    ax.axhline(1e-4, color=INK2, lw=0.8, ls="--")
    style(ax, k, k["titles"][1], "bit error rate")
    ax.legend(frameon=False, fontsize=k["f_leg"], labelcolor=INK, loc="lower right", bbox_to_anchor=(1.0, 0.07))
    # (c) R3 MSE for three step sizes, and R2
    ax = axs[2]
    for (p, col, mk) in MU:
        d = load(10, p)
        if d:
            xs, ys, _ = xy(d, "mse", 1)
            line(ax, k, xs, ys, col, mk, f"R3, $\\mu=2^{{-{p}}}$", f"$2^{{-{p}}}$")
    xs, ys, _ = xy(base, "mse", 0)
    ax.plot(xs, ys, color="#eb6834", lw=k["lw"], marker="^", ms=k["ms"], mec=SURF, mew=k["mew"], label="R2 frozen, $\\mu=2^{-8}$")
    style(ax, k, k["titles"][2], "mean-square error")
    ax.legend(frameon=False, fontsize=k["f_leg"], labelcolor=INK, loc="center left", bbox_to_anchor=(0.0, 0.62))
    if report:
        fig.tight_layout(pad=0.4, w_pad=1.2)
        out = os.path.join(HERE, "..", "report", "figs", "board.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, facecolor=SURF)
    else:
        fig.suptitle("L5 - measured on the Boolean Board (XC7S50, B_mul = 12, B_acc = 16, rounding); primary channel; LFSR noise; "
                     "supervised LMS; 20M symbols per point", color=INK, fontsize=10, x=0.01, ha="left")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        out = os.path.join(RES, "fig_L5_board_tracking.png")
        fig.savefig(out, dpi=150, facecolor=SURF)
    print("written", out)


if __name__ == "__main__":
    main()
