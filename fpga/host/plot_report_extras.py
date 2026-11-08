# plot_report_extras.py -- two figures for the final report:
#   final_report/figs/teaser.pdf  the P5 image decoded by R1, R2, R3 on the Boolean Board (level L5, from results/payload/)
#   final_report/figs/appmap.pdf  illustrative map of real channels against the measured tracking limit (normalised rate)
# Application map: f_D = v f_c / c, nu = f_D T_s = f_D / R_s, from the parameter ranges in APPS (textbook formula, not
# measurements).  Limit lines: nu* = 1 / (152 S*) -- one full triangle period of the primary trajectory per 1/nu symbols --
# with S*_MSE of the L1 final sweep (primary channel, 16 dB): 112, 28, 10 for mu = 2^-10, 2^-8, 2^-6.  The triangle trajectory
# is a deterministic stand-in for random fading, so the map is an order-of-magnitude comparison only.
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results", "payload")
FIGS = os.path.join(HERE, "..", "..", "final_report", "figs")
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BAR, LIM = "#86b6ef", "#184f95"

C_LIGHT, C_SOUND = 3e8, 1500.0
# name, carrier frequency range (Hz), speed range (m/s), symbol rate range (symbol/s), propagation speed
APPS = [
    ("HF skywave modem\n(Doppler spread 0.1-1 Hz, 2400 Bd)", None, None, (2400, 2400), None, (0.1, 1.0)),
    ("Vehicular link, 2 GHz,\n30-120 km/h, 1 Msymbol/s", (2e9, 2e9), (30 / 3.6, 120 / 3.6), (1e6, 1e6), C_LIGHT, None),
    ("Single-carrier cellular, 900 MHz,\n3-250 km/h, 270.8 ksymbol/s", (9e8, 9e8), (3 / 3.6, 250 / 3.6), (270.8e3, 270.8e3), C_LIGHT, None),
    ("High-speed rail, 900 MHz,\n200-350 km/h, 270.8 ksymbol/s", (9e8, 9e8), (200 / 3.6, 350 / 3.6), (270.8e3, 270.8e3), C_LIGHT, None),
    ("Underwater acoustic, 10-20 kHz,\n0.5-2 m/s, 2-10 ksymbol/s", (10e3, 20e3), (0.5, 2.0), (2e3, 10e3), C_SOUND, None),
]
LIMITS = [("$\\mu=2^{-10}$", 112), ("$\\mu=2^{-8}$", 28), ("$\\mu=2^{-6}$", 10)]


def nu_range(app):
    name, fc, v, rs, c, fd_direct = app
    if fd_direct:
        fd_lo, fd_hi = fd_direct
    else:
        fd_lo, fd_hi = v[0] * fc[0] / c, v[1] * fc[1] / c
    return fd_lo / rs[1], fd_hi / rs[0]


def appmap():
    fig, ax = plt.subplots(figsize=(3.4, 2.55), facecolor=SURF)
    ax.set_facecolor(SURF)
    rows = []
    for i, app in enumerate(APPS):
        lo, hi = nu_range(app)
        rows.append((app[0], lo, hi))
        ax.barh(i, hi - lo, left=lo, height=0.5, color=BAR, edgecolor=SURF, linewidth=1)
    for (lab, S), ha in zip(LIMITS, ("right", "center", "left")):    # labels left of, on and right of their lines
        nu = 1.0 / (152 * S)
        ax.axvline(nu, color=LIM, lw=1.1, ls="--")
        ax.text(nu * (0.92 if ha == "right" else 1.08 if ha == "left" else 1.0), -0.75, lab, color=INK, fontsize=5.5,
                ha=ha, va="bottom")
    ax.set_xscale("log")
    ax.set_xlim(5e-6, 2e-2)
    ax.set_yticks(range(len(APPS)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=5)
    ax.set_ylim(len(APPS) - 0.5, -0.85)                         # top row first, room for the limit labels
    ax.set_xlabel("normalised variation $f_D T_s$ (cycles/symbol)", fontsize=6, color=INK2)
    ax.tick_params(axis="x", labelsize=5.5, colors=INK2)
    ax.tick_params(axis="y", length=0, colors=INK)
    ax.grid(True, axis="x", which="major", color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    fig.tight_layout(pad=0.3)
    out = os.path.join(FIGS, "appmap.pdf")
    fig.savefig(out, facecolor=SURF, bbox_inches="tight", pad_inches=0.02)
    print("written", out)
    for name, lo, hi in rows:
        print(f"  {name.splitlines()[0]:40s} nu = {lo:.2e} .. {hi:.2e}")
    for lab, S in LIMITS:
        print(f"  limit {lab}: S* = {S}, nu* = {1 / (152 * S):.2e}")


def teaser():
    m = {r["scenario"]: r for r in json.load(open(os.path.join(RES, "image_metrics.json")))["rows"]}
    rows = [("10dB_S1000", "$S=1000$, $\\mu=2^{-8}$"), ("10dB_S1_mu2-5", "$S=1$, $\\mu=2^{-5}$")]
    orig = mpimg.imread(os.path.join(RES, "image_original_128x72.png"))
    fig, ax = plt.subplots(2, 4, figsize=(7.0, 2.35), facecolor=SURF)
    names = {"R1": "R1 direct", "R2": "R2 frozen LMS", "R3": "R3 adaptive LMS"}
    for i, (sc, lab) in enumerate(rows):
        r = m[sc]
        ims = [orig] + [mpimg.imread(os.path.join(RES, f"image_{sc}_{rx}.png")) for rx in ("R1", "R2", "R3")]
        titles = ["transmitted"] + [f"{names[rx]}: {w} wrong pixels" for rx, w in zip(("R1", "R2", "R3"), r["wrong_pixels"])]
        for j in range(4):
            a = ax[i, j]
            a.imshow(ims[j], interpolation="nearest")
            a.set_xticks([]); a.set_yticks([])
            for s in a.spines.values(): s.set_visible(False)
            a.set_title(titles[j], fontsize=6.5, color=INK, pad=2)
        ax[i, 0].set_ylabel(lab, fontsize=6, color=INK2)
    fig.tight_layout(pad=0.3, h_pad=0.6, w_pad=0.4)
    out = os.path.join(FIGS, "teaser.pdf")
    fig.savefig(out, facecolor=SURF, bbox_inches="tight", pad_inches=0.02)
    print("written", out)


if __name__ == "__main__":
    teaser()
    appmap()
