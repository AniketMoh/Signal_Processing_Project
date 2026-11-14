# confirm_analyse.py -- runs the mid-term analysis (sweep_analyse.analyse, unchanged) on the board sweeps and compares with L1.
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
# For every board raw file results/confirm/board_<channel>_<snr>_<build>_raw.npz:
#   * board analysis with the 7 FPGA step sizes                                    -> analysis_board_<...>.json / _log.txt
#   * L1 analysis restricted to the same 7 step sizes (same rule, same grid)       -> analysis_L1oct_<channel>_<snr>.json
#     (the mid-term's published L1 analysis used 14 half-octave step sizes; mu_opt and its exponent depend on the grid, so the
#      like-for-like comparison is L1 on the octave grid; the published 14-point values are listed beside it)
#   * comparison table (markdown) and figures
#   python confirm_analyse.py
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MID = os.path.join(REPO, "midterm_mtr-22", "2_code_and_results_by_phase")
sys.path.insert(0, os.path.join(MID, "00_shared_library", "code")); sys.path.insert(0, os.path.join(MID, "01_method_pilot_and_statistics_checks", "code"))
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sweep_analyse import analyse

L1RES = os.path.join(MID, "05_P3-P4_boundary_and_optimum_step", "results")
OUT = os.path.join(HERE, "..", "results", "confirm")
S_LIST = [5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1]
P_FPGA = [5, 6, 7, 8, 9, 10, 11]; MUS = [2.0 ** -p for p in P_FPGA]
NODES = {"primary": ((40, 116), [40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 116]), "control": ((26, 77), [26, 34, 42, 50, 58, 66, 74, 77])}


def l1_octave_subset(src_tag, seeds_n):
    """L1 raw (final_<src_tag>_raw.npz) restricted to the board's powers of two (MUS) and to the first seeds_n seeds."""
    src = os.path.join(L1RES, f"final_{src_tag}_raw.npz"); dst = os.path.join(OUT, f"L1oct_{src_tag}_s{seeds_n}_raw.npz")
    if os.path.exists(dst):
        return dst
    R = np.load(src); mus = list(R["meta|mus"]); idx = [int(np.argmin([abs(m - mu) for m in mus])) for mu in MUS]
    o = {}
    for k in R.files:
        v = R[k]
        if k.startswith("meta|"):
            continue
        if v.ndim == 2 and v.shape[0] == len(mus):
            o[k] = v[idx][:, :seeds_n]
        elif k.endswith("|bits"):
            o[k] = np.array([int(v[0]) // R[k.replace("|bits", "|E3")].shape[1] * seeds_n])
        else:
            o[k] = v
    for k in ("meta|S_list", "meta|static_c", "meta|channel", "meta|n_t", "meta|paired"):
        o[k] = R[k]
    o["meta|mus"] = np.array(MUS); o["meta|seeds"] = R["meta|seeds"][:seeds_n]; o["meta|static_seeds"] = R["meta|static_seeds"][:seeds_n]
    np.savez_compressed(dst, **o)
    return dst


def run(raw, channel, snr, seeds, tag):
    (lo, hi), nodes = NODES[channel]
    cfg = dict(channel=(lo, hi), S_list=S_LIST, mus=MUS, seeds=seeds, static_seeds=seeds, static_c=nodes)
    lines = []
    A = analyse(raw, cfg, float(snr), out_json=os.path.join(OUT, f"analysis_{tag}.json"), log=lines.append)
    open(os.path.join(OUT, f"analysis_{tag}_log.txt"), "w").write("\n".join(lines))
    return A


def main():
    global MUS, P_FPGA
    md = ["# Mid-term findings re-measured on the Boolean Board (L5) vs the mid-term simulation (L1)", "",
          "Board: supervised LMS, LFSR sum-of-uniforms noise, fixed point of the loaded build. L1: float, Gaussian noise. Same grid, rules "
          "and analysis code (sweep_analyse.analyse, unchanged); L1 restricted to the same 7 step sizes and seeds.", ""]
    only = sys.argv[1:]                                                         # optional: names (channel_snr_build) to analyse
    for raw in sorted(glob.glob(os.path.join(OUT, "board_*_raw.npz"))):
        name = os.path.basename(raw)[len("board_"):-len("_raw.npz")]          # channel_snr_build
        if only and name not in only:
            continue
        channel, snr, build = name.split("_", 2)
        R = np.load(raw); seeds = list(R["meta|seeds"]); ns = len(seeds)
        MUS = [float(m) for m in R["meta|mus"]]; P_FPGA = [int(round(-np.log2(m))) for m in MUS]     # 7 FPGA mu, or 5 for ber14
        src_tag = "primary_14_ber14" if name.endswith("_ber14") else f"{channel}_{snr}"
        B = run(raw, channel, snr, seeds, f"board_{name}")
        l1raw = l1_octave_subset(src_tag, ns)
        L = run(l1raw, channel, snr, seeds, f"L1oct_{src_tag}_s{ns}")
        pub = json.load(open(os.path.join(L1RES, "final", f"analysis_{src_tag}.json")))
        md += [f"## {channel} channel, {snr} dB, build {build}, {ns} seeds", "",
               "| mu | S*_MSE board | S*_MSE L1 (same mu) | S*_MSE L1 published | S*_BER board | S*_BER L1 | S*_BER L1 published | S_cross board | S_cross L1 | static eps board / L1 |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for mu, p in zip(MUS, P_FPGA):
            b, l = B["res"][str(mu)], L["res"][str(mu)]
            pk = min(pub["res"], key=lambda k: abs(float(k) - mu)); pp = pub["res"][pk]
            def fb(r):
                x = r["ber"].get(2.0, r["ber"].get("2.0"))
                return f"{x['S_star']} ({(x['S_star_kind'] or '-').split(' ')[0]})" if x["S_star"] else f"bracket {x['transition_bracket']}"
            md.append(f"| 2^-{p} | {b['mse']['traj_0.5'][1]} | {l['mse']['traj_0.5'][1]} | {pp['mse']['traj_0.5'][1]} | {fb(b)} | {fb(l)} | {fb(pp)} | "
                      f"{b['cross']['S_first_without'] or 'none'} | {l['cross']['S_first_without'] or 'none'} | "
                      f"{b['rows'][0]['eps_st_traj']:.3f} / {l['rows'][0]['eps_st_traj']:.3f} |")
        eb = B["exponent"]["variants"]; el = L["exponent"]["variants"]; ep = pub["exponent"]["variants"]
        base = "V0 baseline (3-pt parabola, bracketed, rho<=0.75)"
        md += ["", f"mu_opt exponent (baseline variant): board {eb[base][0]} ({eb[base][1]} pts), L1 7-mu {el[base][0]} ({el[base][1]} pts), "
                   f"L1 published 14-mu {ep[base][0]}; board spread {eb['spread']}, L1 7-mu spread {el['spread']}", ""]
        # per-point MSE agreement
        rel = []
        for S in S_LIST:
            jb = R[f"{snr}|{S}|J3"]; jl = np.load(l1raw)[f"{snr}|{S}|J3"]
            rel.append((jb.mean(axis=1) - jl.mean(axis=1)) / jl.mean(axis=1))
        rel = np.array(rel)
        md += [f"R3 MSE board vs L1, relative difference over all (S, mu): median {np.median(rel) * 100:+.2f} %, "
               f"range {rel.min() * 100:+.2f} .. {rel.max() * 100:+.2f} %", ""]
        st = R[f"{snr}|28|ST"].sum(axis=1) / R[f"{snr}|28|UP"].sum(axis=1)
        md += ["Stall fraction at S = 28 (board): " + ", ".join(f"2^-{p}: {s * 100:.2f} %" for p, s in zip(P_FPGA, st)), ""]
        figs(B, L, R, name, channel, snr, ns)
    open(os.path.join(OUT, "confirm_summary.md" if not only else f"confirm_summary_{'_'.join(only)}.md"), "w").write("\n".join(md))
    print("\n".join(md))


def figs(B, L, R, name, channel, snr, ns):
    S = np.array(S_LIST, float); cm = plt.cm.viridis
    fig, ax = plt.subplots(1, 3, figsize=(18, 5.2))
    for j, (mu, p) in enumerate(zip(MUS, P_FPGA)):
        col = cm(j / max(1, len(MUS) - 1))
        ax[0].semilogx(S, [r["rho_traj"][0] for r in B["res"][str(mu)]["rows"]], "o-", color=col, ms=3, label=f"2^-{p} board")
        ax[0].semilogx(S, [r["rho_traj"][0] for r in L["res"][str(mu)]["rows"]], "--", color=col, lw=0.9)
    ax[0].axhline(0.5, color="k", lw=0.8, ls=":"); ax[0].invert_xaxis(); ax[0].set_ylim(-0.2, 1.6)
    ax[0].set_xlabel("S (smaller = faster)"); ax[0].set_ylabel("tracking loss rho"); ax[0].legend(fontsize=7, ncol=2)
    ax[0].set_title("Tracking loss: board (solid) vs L1 (dashed)", fontsize=10)
    for res, mk, nm in ((B, "o-", "board"), (L, "s--", "L1 (7 mu)")):
        y = [res["res"][str(m)]["mse"]["traj_0.5"][1] for m in MUS]
        ax[1].loglog([m for m, v in zip(MUS, y) if v], [v for v in y if v], mk, label=f"S*_MSE {nm}")
    ax[1].loglog(MUS, [0.11 / m for m in MUS], "k:", lw=0.8, label="0.11 / mu (mid-term law)")
    ax[1].set_xlabel("mu"); ax[1].set_ylabel("S*_MSE"); ax[1].legend(fontsize=8); ax[1].set_title("Tracking boundary vs step size", fontsize=10)
    for res, mk, nm in ((B, "o-", "board"), (L, "s--", "L1 (7 mu)")):
        mo = res["mu_opt"]; ok = [m["bracketed"] for m in mo]
        ax[2].loglog([1 / m["S"] for m, o in zip(mo, ok) if o], [2 ** m["log2mu_refined"] for m, o in zip(mo, ok) if o], mk, label=f"mu_opt {nm}")
    ax[2].set_xlabel("variation rate 1/S"); ax[2].set_ylabel("optimum step size"); ax[2].legend(fontsize=8)
    ax[2].set_title("Optimum step size vs variation rate", fontsize=10)
    fig.suptitle(f"Mid-term P3/P4 findings on the board: {channel} channel, {snr} dB, {ns} seeds ({name})", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"fig_confirm_{name}.png"), dpi=120); plt.close(fig)


if __name__ == "__main__":
    main()
