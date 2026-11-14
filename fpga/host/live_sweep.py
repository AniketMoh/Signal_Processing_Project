# live_sweep.py -- live tracking curve for the viva: short host-mode runs on the Boolean Board over the variation rate S,
# BER of R1/R2/R3 plotted point by point as the board measures them (level L5, single seed, short runs).
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
#   python live_sweep.py                       mu = 2^-8, 10 dB, 2 M symbols per point
#   python live_sweep.py --mus 6 8 10          overlay R3 for mu = 2^-6, 2^-8, 2^-10
#   python live_sweep.py --ebn0 12 --n 4e6 --loop
# Options: --port COMx, --save (write the figure to results/live/), --loop (repeat until the window is closed)
# Display only: nothing is written to the saved sweep results (results/board_sweep_*.json stay as they are).
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from run_board import Board, find_port, RESULTS

GRID = [5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1]
COL = {"R1": "#9e9e9e", "R2": "#e8710a", "R3": "#1a73e8"}
MU_STYLE = {6: ("#0b8043", "v"), 8: ("#1a73e8", "o"), 10: ("#8e24aa", "s"), 7: ("#00897b", "^"), 9: ("#3949ab", "D")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--mus", type=int, nargs="+", default=[8], help="step sizes as exponents p (mu = 2^-p)")
    ap.add_argument("--ebn0", type=float, default=10.0)
    ap.add_argument("--n", type=float, default=2e6, help="tracking symbols per point (about n / 6.25e6 s each)")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()

    import l2_ref as R
    b = Board(a.port or find_port())
    ident = b.ident()
    print("board:", ident)
    states = R.ff.lfsr_start_values(2000 + 500000)
    sq = R.ff.sigma_q_from_ebn0(a.ebn0)
    nt = 30000

    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.canvas.manager.set_window_title("Live tracking curve -- Boolean Board (L5)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(8000, 0.7)                                       # inverted: faster channel to the right
    ax.set_ylim(1e-6, 1e-1)
    ax.set_xlabel("variation rate S  (symbols per channel step)   → faster channel")
    ax.set_ylabel("bit error rate")
    ax.grid(True, which="both", alpha=0.25)
    title = ax.set_title("")
    lines, statics, texts = {}, {}, {}
    for p in a.mus:
        c, m = MU_STYLE.get(p, ("#1a73e8", "o"))
        lab = f"R3 adaptive LMS, μ = 2^-{p}"
        lines[("R3", p)], = ax.plot([], [], "-" + m, color=c, lw=2.2, ms=6, label=lab)
    lines[("R2", 0)], = ax.plot([], [], "-o", color=COL["R2"], lw=1.8, ms=5, label="R2 frozen equaliser")
    lines[("R1", 0)], = ax.plot([], [], "-o", color=COL["R1"], lw=1.5, ms=4, label="R1 no equaliser")
    ax.legend(loc="lower right")
    status = fig.text(0.01, 0.01, "", fontsize=10, family="monospace")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plt.pause(0.05)

    sweep_no = 0
    while plt.fignum_exists(fig.number):
        sweep_no += 1
        for line in lines.values():
            line.set_data([], [])
        data = {k: ([], []) for k in lines}
        for i, p in enumerate(a.mus):
            title.set_text(f"Boolean Board, live: BER vs channel speed   {a.ebn0:g} dB, μ = 2^-{p}"
                           f"   ({int(a.n / 1e6) if a.n >= 1e6 else a.n:g}M symbols per point, sweep {sweep_no})")
            for S in [None] + GRID:
                if not plt.fignum_exists(fig.number):
                    return 0
                per = 152 * S if S else 1
                ne = max(1, round(a.n / per)) * per if S else int(a.n)
                rep, dt = b.run(p, S, 40, 116, sq, nt, nt + ne, 777, states)
                n, e1, e2, e3 = rep["counters"][:4]
                ber = {"R1": e1 / n, "R2": e2 / n, "R3": e3 / n}
                if S is None:                                    # static channel: dashed reference line for R3
                    c, _ = MU_STYLE.get(p, ("#1a73e8", "o"))
                    if p in statics:
                        statics[p].remove()
                    statics[p] = ax.axhline(max(ber["R3"], 1.1e-6), color=c, ls=":", lw=1,
                                            label=f"R3 static channel, μ = 2^-{p}")
                    ax.legend(loc="lower right")
                    status.set_text(f"static channel: R1 {ber['R1']:.1e}  R2 {ber['R2']:.1e}  R3 {ber['R3']:.1e}")
                else:
                    keys = [("R3", p)] + ([("R2", 0), ("R1", 0)] if i == 0 else [])
                    for k in keys:
                        xs, ys = data[k]; xs.append(S); ys.append(max(ber[k[0]], 1e-6))
                        lines[k].set_data(xs, ys)
                    status.set_text(f"S = {S:>4}  ({n / 1e6:.1f}M symbols, {dt:.2f} s):  errors R1 {e1:>7}  R2 {e2:>6}  "
                                    f"R3 {e3:>5}    BER R3 {ber['R3']:.2e}")
                    print(f"mu=2^-{p} S={S:>5}: BER R1 {ber['R1']:.2e}  R2 {ber['R2']:.2e}  R3 {ber['R3']:.2e}")
                fig.canvas.draw_idle(); plt.pause(0.01)
        if a.save:
            os.makedirs(os.path.join(RESULTS, "live"), exist_ok=True)
            out = os.path.join(RESULTS, "live", f"live_sweep_{a.ebn0:g}dB_mu{'_'.join(map(str, a.mus))}.png")
            fig.savefig(out, dpi=150); print("saved", out)
        if not a.loop:
            break
    status.set_text(status.get_text() + "    -- done (close the window to exit)")
    plt.ioff(); plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
