# plot_confirm_report.py -- report figure for the board re-measurement of the mid-term findings -> final_report/figs/confirm.pdf
# Every number is read from results/confirm (board raw files and the analyses written by confirm_analyse.py).
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#   python plot_confirm_report.py
import json, os, sys
from math import comb, factorial
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MID = os.path.join(REPO, "midterm_mtr-22", "2_code_and_results_by_phase")
sys.path.insert(0, os.path.join(MID, "00_shared_library", "code"))
import numpy as np
import report_style as RS
import matplotlib.pyplot as plt
from scipy.stats import norm
from config import sigma_from_ebn0

OUT = os.path.join(HERE, "..", "results", "confirm")
FIG = os.path.join(REPO, "final_report", "figs", "confirm.pdf")
S_LIST = [5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1]
P = [5, 6, 7, 8, 9, 10, 11]
CONFIGS = [("primary_16", "primary 16 dB", "o"), ("primary_14", "primary 14 dB", "s"), ("primary_12", "primary 12 dB", "D"),
           ("control_16", "control 16 dB", "^"), ("control_14", "control 14 dB", "v")]


def ih_sf(t, n=12):
    x = t + n / 2.0
    if x >= n: return 0.0
    if x <= 0: return 1.0
    return 1 - sum((-1) ** k * comb(n, k) * (x - k) ** n for k in range(int(np.floor(x)) + 1)) / factorial(n)


def r1(a, snr, sf):
    s = sigma_from_ebn0(snr)
    return float(np.mean([sf((1 + s1 * a + s2 * 0.1) / s) for s1 in (1, -1) for s2 in (1, -1)]))


def main():
    RS.apply()
    J = lambda n: json.load(open(os.path.join(OUT, f"analysis_{n}.json")))
    fig, ax = plt.subplots(1, 4, figsize=(RS.TXT_W, 1.95))
    # (a) rho vs S, primary 16 dB
    Bd, Ld = J("board_primary_16_m12_a16_r1"), J("L1oct_primary_16_s100")
    shades = {6: "#9cc3ee", 8: "#2a78d6", 10: "#0b3a73"}
    for p, col in shades.items():
        mu = str(2.0 ** -p)
        ax[0].semilogx(S_LIST, [r["rho_traj"][0] for r in Bd["res"][mu]["rows"]], "o", color=col, ms=2.6, label=f"$2^{{-{p}}}$ board")
        ax[0].semilogx(S_LIST, [r["rho_traj"][0] for r in Ld["res"][mu]["rows"]], "-", color=col, lw=0.9)
    ax[0].axhline(0.5, color=RS.GREY, lw=0.7, ls=":")
    ax[0].invert_xaxis(); ax[0].set_ylim(-0.1, 1.3); ax[0].set_xlabel("$S$ (faster $\\rightarrow$)"); ax[0].set_ylabel("tracking loss $\\rho$")
    ax[0].plot([], [], "-", color=RS.GREY, lw=0.9, label="L1"); ax[0].legend(fontsize=5.8, loc="upper left"); ax[0].set_title("(a) primary, 16 dB", fontsize=7.5)
    # (b) S*_MSE vs mu, all configurations
    mus = [2.0 ** -p for p in P]
    for tag, lab, mk in CONFIGS:
        b, l = J(f"board_{tag}_m12_a16_r1"), J(f"L1oct_{tag}_s100")
        yb = [b["res"][str(m)]["mse"]["traj_0.5"][1] for m in mus]; yl = [l["res"][str(m)]["mse"]["traj_0.5"][1] for m in mus]
        ax[1].loglog([m for m, v in zip(mus, yl) if v], [v for v in yl if v], "-", color=RS.GREY, lw=0.6)
        ax[1].loglog([m for m, v in zip(mus, yb) if v], [v for v in yb if v], mk, ms=3, mfc="none", label=lab)
    ax[1].loglog(mus, [0.11 / m for m in mus], ":", color=RS.THEORY, lw=0.8, label="$0.11/\\mu$")
    ax[1].set_xlabel("$\\mu$"); ax[1].set_ylabel("$S^\\star_{\\rm MSE}$"); ax[1].legend(fontsize=5.0, loc="lower left", handletextpad=0.3, labelspacing=0.25)
    ax[1].set_title("(b) boundary: board = L1", fontsize=7.5)
    # (c) R1 on static channels vs a: board, Gaussian, sum of 12 uniforms
    aa = np.linspace(0.3, 0.92, 80)
    for snr, col in ((16, RS.EXTRA[0]), (14, RS.EXTRA[1]), (12, RS.EXTRA[2])):
        R = np.load(os.path.join(OUT, f"board_primary_{snr}_m12_a16_r1_raw.npz")); cs = R["meta|static_c"]
        ber = [R[f"{snr}|static_c{c}|E1"][0].sum() / int(R[f"{snr}|static_c{c}|bits"][0]) for c in cs]
        ax[2].semilogy([c / 128 for c, v in zip(cs, ber) if v > 0], [v for v in ber if v > 0], "o", color=col, ms=2.6, label=f"board {snr} dB")
        ax[2].semilogy(aa, [r1(a, snr, norm.sf) for a in aa], "--", color=col, lw=0.7)
        ax[2].semilogy(aa, [r1(a, snr, ih_sf) for a in aa], "-", color=col, lw=0.7)
    ax[2].plot([], [], "--", color=RS.GREY, lw=0.7, label="Gaussian"); ax[2].plot([], [], "-", color=RS.GREY, lw=0.7, label="sum of 12 unif.")
    ax[2].axhline(1e-4, color=RS.GREY, lw=0.5, ls=":")
    ax[2].set_ylim(1e-7, 0.5); ax[2].set_xlabel("static channel $a$"); ax[2].set_ylabel("R1 BER"); ax[2].legend(fontsize=5.3, loc="lower right")
    ax[2].set_title("(c) hardware noise tails", fontsize=7.5)
    # (d) paired cost of the 16-bit accumulator
    A = np.load(os.path.join(OUT, "board_primary_16_m12_a16_r1_raw.npz")); B = np.load(os.path.join(OUT, "board_primary_16_m12_a26_r1_raw.npz"))
    for p, col in ((9, "#9cc3ee"), (10, "#2a78d6"), (11, "#0b3a73")):
        j = P.index(p)
        d = [100 * np.mean((A[f"16|{s}|J3"][j] - B[f"16|{s}|J3"][j]) / B[f"16|{s}|J3"][j]) for s in S_LIST]
        ax[3].semilogx(S_LIST, d, "o-", color=col, ms=2.4, lw=0.9, label=f"$2^{{-{p}}}$")
    ax[3].invert_xaxis(); ax[3].set_xlabel("$S$ (faster $\\rightarrow$)"); ax[3].set_ylabel("MSE cost of 16 bit (%)")
    ax[3].legend(fontsize=5.8, loc="upper right"); ax[3].set_title("(d) $B_{\\rm acc}$ 16 vs 26, paired", fontsize=7.5)
    fig.tight_layout(w_pad=0.6)
    fig.savefig(FIG); fig.savefig(os.path.join(OUT, "fig_confirm_report.png"), dpi=200)
    print("wrote", FIG)


if __name__ == "__main__":
    main()
