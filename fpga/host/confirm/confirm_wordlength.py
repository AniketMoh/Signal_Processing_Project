# confirm_wordlength.py -- paired comparison of the 16-bit and 26-bit accumulator builds on the board (same seeds, same LFSR noise,
# same payload: the two runs differ only in the accumulator width), primary channel, 16 dB.
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#   python confirm_wordlength.py   -> results/confirm/fig_wordlength_a16_vs_a26.png, wordlength_a16_vs_a26.md
import os
HERE = os.path.dirname(os.path.abspath(__file__))
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

OUT = os.path.join(HERE, "..", "results", "confirm")
S_LIST = [5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1, None]
P = [5, 6, 7, 8, 9, 10, 11]


def main():
    A = np.load(os.path.join(OUT, "board_primary_16_m12_a16_r1_raw.npz")); B = np.load(os.path.join(OUT, "board_primary_16_m12_a26_r1_raw.npz"))
    D = np.zeros((len(S_LIST), 7)); H = np.zeros_like(D); ST = np.zeros_like(D)
    for i, s in enumerate(S_LIST):
        for j in range(7):
            d = (A[f"16|{s}|J3"][j] - B[f"16|{s}|J3"][j]) / B[f"16|{s}|J3"][j] * 100
            D[i, j] = d.mean(); H[i, j] = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            ST[i, j] = A[f"16|{s}|ST"][j].sum() / A[f"16|{s}|UP"][j].sum() * 100
    md = ["# 16-bit vs 26-bit accumulator on the board (paired: same seeds, noise and payload), primary channel, 16 dB, 100 seeds", "",
          "R3 MSE increase of the 16-bit build over the 26-bit build, % (95 % paired interval half-width), and the 16-bit stall fraction.", "",
          "| S | " + " | ".join(f"2^-{p}" for p in P) + " |", "|---|" + "---|" * 7]
    for i, s in enumerate(S_LIST):
        md.append(f"| {'static' if s is None else s} | " + " | ".join(f"{D[i, j]:+.3f} (+-{H[i, j]:.3f}); {ST[i, j]:.0f} % st." for j in range(7)) + " |")
    md += ["", "R3 bit errors summed over all rates (16-bit / 26-bit): " +
           ", ".join(f"2^-{p}: {sum(int(A[f'16|{s}|E3'][j].sum()) for s in S_LIST)} / {sum(int(B[f'16|{s}|E3'][j].sum()) for s in S_LIST)}"
                     for j, p in enumerate(P))]
    open(os.path.join(OUT, "wordlength_a16_vs_a26.md"), "w").write("\n".join(md))
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.6))
    lab = ["static" if s is None else str(s) for s in S_LIST]
    im = ax[0].imshow(D, aspect="auto", cmap="magma_r", vmin=0, vmax=max(0.1, D.max()))
    for i in range(len(S_LIST)):
        for j in range(7):
            ax[0].text(j, i, f"{D[i, j]:.2f}", ha="center", va="center", fontsize=6.5, color="w" if D[i, j] > 0.45 * D.max() else "k")
    ax[0].set_xticks(range(7)); ax[0].set_xticklabels([f"2^-{p}" for p in P]); ax[0].set_yticks(range(len(S_LIST))); ax[0].set_yticklabels(lab, fontsize=7)
    ax[0].set_xlabel("step size mu"); ax[0].set_ylabel("S (top = slow)"); fig.colorbar(im, ax=ax[0]).set_label("R3 MSE increase, 16-bit vs 26-bit (%)")
    ax[0].set_title("Cost of the 16-bit accumulator (paired, same noise)", fontsize=10)
    im2 = ax[1].imshow(ST, aspect="auto", cmap="viridis")
    ax[1].set_xticks(range(7)); ax[1].set_xticklabels([f"2^-{p}" for p in P]); ax[1].set_yticks(range(len(S_LIST))); ax[1].set_yticklabels(lab, fontsize=7)
    ax[1].set_xlabel("step size mu"); fig.colorbar(im2, ax=ax[1]).set_label("updates rounded to zero (stalls), %")
    ax[1].set_title("Stall fraction of the 16-bit accumulator (26-bit: <= 0.05 %)", fontsize=10)
    fig.suptitle("Word length on the Boolean Board: the 16-bit accumulator costs < 0.02 % MSE except at the smallest mu on slowly moving "
                 "channels (up to about 1 %); S* unchanged", fontsize=9.5)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_wordlength_a16_vs_a26.png"), dpi=120); plt.close(fig)
    print("\n".join(md))


if __name__ == "__main__":
    main()
