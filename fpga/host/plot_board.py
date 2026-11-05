# plot_board.py -- figure of the board sweeps (level L5): BER of R1/R2/R3 and R3 MSE against the variation rate S.
# Reads results/board_sweep_*.json written by run_board.py; writes results/fig_L5_board_tracking.png.
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = "m12_a16_r1"                                  # default board build
RES = os.path.join(HERE, "results")
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
RX = [("R1 direct", "#2a78d6", "s"), ("R2 frozen", "#eb6834", "^"), ("R3 adaptive", "#1baf7a", "o")]
MU = [("6", "#86b6ef", "D"), ("8", "#2a78d6", "o"), ("10", "#184f95", "v")]       # one hue, light -> dark = larger -> smaller mu


def load(eb, p):
    f = os.path.join(RES, f"board_sweep_{BUILD}_{eb}dB_mu2-{p}.json")
    return json.load(open(f)) if os.path.isfile(f) else None


def xy(d, key, i):
    rows = [r for r in d["rows"] if r["S"] is not None]
    xs = [r["S"] for r in rows]
    ys = [max(r[key][i], 1e-7) for r in rows]
    st = [r for r in d["rows"] if r["S"] is None][0][key][i]
    return xs, ys, st


def style(ax, title, ylabel):
    ax.set_facecolor(SURF)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.invert_xaxis()
    ax.grid(True, which="major", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.set_xlabel("symbols per channel step S (faster variation to the right)", color=INK2, fontsize=9)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.set_title(title, color=INK, fontsize=10, loc="left")


def main():
    base = load(10, 8)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), facecolor=SURF)
    # (a) the three receivers, 10 dB, mu = 2^-8
    ax = axs[0]
    for i, (name, col, mk) in enumerate(RX):
        xs, ys, st = xy(base, "ber", i)
        ax.plot(xs, ys, color=col, lw=2, marker=mk, ms=6, mec=SURF, mew=1.5, label=name)
        ax.axhline(max(st, 1e-7), color=col, lw=1, ls=":", alpha=0.8)
        ax.annotate(name, (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points", color=INK, fontsize=8, va="center")
    ax.axhline(1e-4, color=INK2, lw=1, ls="--")
    ax.text(5000, 1.15e-4, "hardware-noise validity limit 1e-4", color=INK2, fontsize=7)
    style(ax, "(a) BER, 10 dB, mu = 2^-8 (dotted: static channel)", "bit error rate")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="center left", bbox_to_anchor=(0.0, 0.2))
    # (b) R3 BER for three step sizes
    ax = axs[1]
    for (p, col, mk) in MU:
        d = load(10, p)
        if not d: continue
        xs, ys, _ = xy(d, "ber", 2)
        ax.plot(xs, ys, color=col, lw=2, marker=mk, ms=6, mec=SURF, mew=1.5, label=f"R3, mu = 2^-{p}")
        ax.annotate(f"2^-{p}", (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points", color=INK, fontsize=8, va="center")
    ax.axhline(1e-4, color=INK2, lw=1, ls="--")
    style(ax, "(b) R3 BER against step size, 10 dB", "bit error rate")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="lower right", bbox_to_anchor=(1.0, 0.07))
    # (c) R3 MSE for three step sizes
    ax = axs[2]
    for (p, col, mk) in MU:
        d = load(10, p)
        if not d: continue
        xs, ys, st = xy(d, "mse", 1)
        ax.plot(xs, ys, color=col, lw=2, marker=mk, ms=6, mec=SURF, mew=1.5, label=f"R3, mu = 2^-{p}")
        ax.annotate(f"2^-{p}", (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points", color=INK, fontsize=8, va="center")
    xs, ys, _ = xy(base, "mse", 0)
    ax.plot(xs, ys, color="#eb6834", lw=2, marker="^", ms=6, mec=SURF, mew=1.5, label="R2 frozen, mu = 2^-8")
    style(ax, "(c) MSE, 10 dB", "mean-square error")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="center left", bbox_to_anchor=(0.0, 0.62))
    fig.suptitle("L5 - measured on the Boolean Board (XC7S50, B_mul = 12, B_acc = 16, rounding); primary channel; LFSR noise; "
                 "supervised LMS; 20M symbols per point", color=INK, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(RES, "fig_L5_board_tracking.png")
    fig.savefig(out, dpi=150, facecolor=SURF)
    print("written", out)


if __name__ == "__main__":
    main()
