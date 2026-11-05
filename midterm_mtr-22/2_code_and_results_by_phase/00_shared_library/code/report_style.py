"""report_style.py -- one plotting style for every figure of the mid-term report.
Only the look changes (fonts, sizes, colours); every number is read from the saved result files.
Colours: fixed per receiver (R1 orange, R2 blue, R3 green), checked for colour-blind separation;
step-size families use one hue from light (small mu) to dark (large mu)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COL_W = 3.3      # one column of the report, inches
TXT_W = 6.9      # full text width, inches

R1, R2, R3 = "#eb6834", "#2a78d6", "#008300"          # direct, frozen, adaptive
RX = {"R1": R1, "R2": R2, "R3": R3}
RXNAME = {"R1": "R1 direct", "R2": "R2 frozen", "R3": "R3 adaptive"}
THEORY = "#222222"                                   # theory / model lines
GREY = "#8a8985"
PRIMARY, CONTROL = "#2a78d6", "#6250d6"              # channels (SNR is shown by marker fill / line style)
EXTRA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BAND = "#e8eef8"                                     # light background band (tolerance, etc.)


def apply():
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Liberation Serif", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5, "legend.fontsize": 7,
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
        "axes.linewidth": 0.6, "axes.edgecolor": "#444444", "axes.labelcolor": "#111111",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.5, "grid.alpha": 1.0,
        "axes.axisbelow": True,
        "xtick.color": "#444444", "ytick.color": "#444444",
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.minor.width": 0.4, "ytick.minor.width": 0.4,
        "lines.linewidth": 1.4, "lines.markersize": 4,
        "legend.frameon": False, "legend.handlelength": 1.8, "legend.borderaxespad": 0.3,
        "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,
    })


def blues(n, lo=0.30, hi=0.95):
    """n shades of one hue, light to dark (small step size light, large step size dark)."""
    cm = plt.get_cmap("Blues")
    return [cm(v) for v in np.linspace(lo, hi, n)]


def panel(ax, letter, x=-0.02, y=1.02):
    ax.text(x, y, f"({letter})", transform=ax.transAxes, fontsize=8.5, fontweight="bold", va="bottom", ha="right")


def mu_label(mu):
    return r"$2^{%g}$" % np.log2(mu)


def save(fig, name, out="results/report_figs"):
    import os
    os.makedirs(out, exist_ok=True)
    place_legends_below(fig)
    fig.savefig(f"{out}/{name}.pdf")
    fig.savefig(f"{out}/{name}.png", dpi=200)
    plt.close(fig)
    print("saved", name, flush=True)


def leg_below(ax, ncol=1, dy=-0.32, fs=6.8, **kw):
    """Legend under the panel (below its x label), so it never covers data."""
    lg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, dy), ncol=ncol, fontsize=fs, handlelength=1.6,
                   columnspacing=1.0, borderaxespad=0.0, **kw)
    ax._leg_below = lg
    return lg


def place_legends_below(fig):
    """Move every leg_below legend just under its panel's x-axis label (measured after layout), so it never overlaps."""
    fig.canvas.draw(); r = fig.canvas.get_renderer()
    for ax in fig.axes:
        lg = getattr(ax, "_leg_below", None)
        if lg is None: continue
        bb = ax.xaxis.get_tightbbox(r)
        y = ax.transAxes.inverted().transform((0, bb.y0))[1]
        lg.set_bbox_to_anchor((0.5, y - 0.03), transform=ax.transAxes)


def leg_top(fig, handles, labels, ncol, fs=6.5, y=1.0):
    """One shared legend above all panels."""
    return fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, y), ncol=ncol, fontsize=fs,
                      handlelength=1.8, columnspacing=1.2)


def collect(axs):
    h, l = [], []
    for ax in axs:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            if ll not in l and not ll.startswith("_"): h.append(hh); l.append(ll)
    return h, l
