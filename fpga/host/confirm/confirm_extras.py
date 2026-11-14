# confirm_extras.py -- further mid-term claims checked on the board data (static runs of the board sweeps).
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#   1. P1: R1 error floor on static ISI channels (mid-term: 14-20 % at a = 0.91 at every SNR) and the noise-generator effect:
#      board BER vs exact Gaussian BER vs exact sum-of-12-uniforms (Irwin-Hall) BER of the hardware noise.
#   2. P1/theory: misadjustment on the control channel, a = 0.60 (c = 77), 14 dB: measured excess MSE / textbook
#      mu tr(R) J_min / 2 (mid-term L1: 1.47-1.48; corrected formula predicts 1.468).
#   3. Word length: static excess MSE and stall fraction per step size for every board build found (16- vs 26-bit accumulator).
#   python confirm_extras.py
import glob, os, sys
from math import comb, factorial
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MID = os.path.join(REPO, "midterm_mtr-22", "2_code_and_results_by_phase")
sys.path.insert(0, os.path.join(MID, "00_shared_library", "code"))
import numpy as np
from scipy.stats import norm
from exp_lib import Rp_const
from config import sigma_from_ebn0

L1RES = os.path.join(MID, "05_P3-P4_boundary_and_optimum_step", "results")
OUT = os.path.join(HERE, "..", "results", "confirm")
P_FPGA = [5, 6, 7, 8, 9, 10, 11]; H2 = 0.1


def ih_sf(t, n=12):
    x = t + n / 2.0
    if x >= n: return 0.0
    if x <= 0: return 1.0
    return 1 - sum((-1) ** k * comb(n, k) * (x - k) ** n for k in range(int(np.floor(x)) + 1)) / factorial(n)


def r1_theory(c, snr):
    s = sigma_from_ebn0(snr); a = c / 128
    m = [(1 + s1 * a + s2 * H2) / s for s1 in (1, -1) for s2 in (1, -1)]
    return float(np.mean([norm.sf(x) for x in m])), float(np.mean([ih_sf(x) for x in m]))


def main():
    md = ["# Further mid-term checks on the board data", ""]
    files = sorted(glob.glob(os.path.join(OUT, "board_*_raw.npz")))
    # 1. R1 static floor and noise distribution
    md += ["## 1. R1 on static ISI channels (P1) and the hardware noise distribution", "",
           "| channel / SNR / build | a | board BER | L1 BER | Gaussian exact | sum-of-12-uniforms exact | board / uniform-sum |", "|---|---|---|---|---|---|---|"]
    for f in files:
        name = os.path.basename(f)[6:-8]; ch, snr, build = name.split("_", 2)
        B = np.load(f); L = np.load(os.path.join(L1RES, f"final_{ch}_{snr}_raw.npz"))
        for c in B["meta|static_c"]:
            k = f"{snr}|static_c{c}|E1"; nb = int(B[f"{snr}|static_c{c}|bits"][0]); nl = int(L[f"{snr}|static_c{c}|bits"][0])
            eb, el = B[k][0].sum() / nb, L[k][0].sum() / nl; g, u = r1_theory(int(c), float(snr))
            md.append(f"| {name} | {c / 128:.3f} | {eb:.3e} | {el:.3e} | {g:.3e} | {u:.3e} | {eb / u if u > 0 else float('nan'):.3f} |")
    # 2. misadjustment, control channel c = 77, 14 dB
    md += ["", "## 2. Misadjustment on the control channel, a = 0.60, 14 dB (mid-term: 1.47-1.48 x textbook)", "",
           "| build | mu | board J3 | L1 J3 (same grid) | mid-term L1 J3 (1e6 symbols) | board ratio | L1 ratio | mid-term ratio | board stall fraction |", "|---|---|---|---|---|---|---|---|---|"]
    # exactly as the mid-term (03_P1_validation/investigate_misadjustment.py): textbook excess = J_min q/(1-q), q = mu tr(R)/2,
    # R of the L-tap equalizer input for h = [1, 77/128, 0.1]; mid-term values: J_min 0.02736, tr(R) 22.269
    from misadj_lib import wiener
    s2 = sigma_from_ebn0(14.0) ** 2; _, Jmin, Rm = wiener(np.array([1.0, 77 / 128, H2]), 2, s2); trR = float(np.trace(Rm))
    MID_J = {7: 0.03125, 8: 0.02919, 9: 0.02825, 10: 0.02779}            # mid-term L1 MSE, 16 seeds x 1e6 symbols (console log)
    note = (f"J_min {Jmin:.5f}, tr(R) {trR:.3f} (mid-term: 0.02736, 22.269). Board and L1 (same grid): 100 seeds x 152000 symbols after "
            "N_T = 30000; statistical uncertainty of J3 about +-0.00003, i.e. about +-0.03 / 0.05 / 0.1 in the ratio at 2^-8 / 2^-9 / 2^-10.")
    for f in [f for f in files if "control_14" in f]:
        B = np.load(f); L = np.load(os.path.join(L1RES, "final_control_14_raw.npz")); mus_l = list(L["meta|mus"])
        for j, p in enumerate(P_FPGA):
            mu = 2.0 ** -p; i = int(np.argmin([abs(m - mu) for m in mus_l])); q = mu * trR / 2; tb = Jmin * q / (1 - q)
            jb = B["14|static_c77|J3"][j].mean(); jl = L["14|static_c77|J3"][i].mean()
            st = B["14|static_c77|ST"][j].sum() / B["14|static_c77|UP"][j].sum()
            mj = MID_J.get(p)
            md.append(f"| {os.path.basename(f)[6:-8].split('_', 2)[2]} | 2^-{p} | {jb:.5f} | {jl:.5f} | {mj if mj else '-'} | {(jb - Jmin) / tb:.3f} | "
                      f"{(jl - Jmin) / tb:.3f} | {f'{(mj - Jmin) / tb:.3f}' if mj else '-'} | {st * 100:.1f} % |")
    md += ["", note]
    # 3. word length: static excess and stalls per build (primary 16 dB)
    md += ["", "## 3. Word length: static channel (c = 40) excess MSE and stalls, primary 16 dB", "",
           "| build | " + " | ".join(f"2^-{p}" for p in P_FPGA) + " |", "|---|" + "---|" * len(P_FPGA)]
    L = np.load(os.path.join(L1RES, "final_primary_16_raw.npz")); mus_l = list(L["meta|mus"])
    jl = [L["16|static_c40|J3"][int(np.argmin([abs(m - 2.0 ** -p) for m in mus_l]))].mean() for p in P_FPGA]
    md.append("| L1 float J3 | " + " | ".join(f"{v:.5f}" for v in jl) + " |")
    for f in [f for f in files if "primary_16" in f]:
        B = np.load(f); b = os.path.basename(f)[6:-8].split("_", 2)[2]
        md.append(f"| {b} J3 | " + " | ".join(f"{B['16|static_c40|J3'][j].mean():.5f}" for j in range(7)) + " |")
        md.append(f"| {b} J3 / L1 | " + " | ".join(f"{B['16|static_c40|J3'][j].mean() / jl[j]:.4f}" for j in range(7)) + " |")
        md.append(f"| {b} stalls | " + " | ".join(f"{B['16|static_c40|ST'][j].sum() / B['16|static_c40|UP'][j].sum() * 100:.1f} %" for j in range(7)) + " |")
    open(os.path.join(OUT, "confirm_extras.md"), "w").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
