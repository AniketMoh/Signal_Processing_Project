# board_midterm_sweep.py -- the mid-term P3/P4 tracking sweep (final_sweep.py, FREEZE-1 grid) re-run on the Boolean Board (level L5).
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
# Same grid as the L1 sweep: 18 rates S + static, the 7 FPGA step sizes 2^-5..2^-11, N_T = 30000, evaluation over whole triangle
# periods (n_eval_for, about 152000 symbols), static baselines at the same counter nodes, seeds 2000.. (noise seed + 500000).
# Differences that cannot be avoided, and are the subject of the comparison:
#   * fixed-point arithmetic of the loaded bitstream (B_MUL, B_ACC, RND) instead of float (L1);
#   * on-chip 12-LFSR sum-of-uniforms noise instead of Gaussian noise; different random numbers for the same seed label;
#   * on-chip payload LFSR (payload seed = noise seed) instead of numpy random bits;
#   * only powers of two for mu (the half-octave L1 grid 2^-5.5, 2^-6.5, ... has no hardware equivalent).
# The reference quantities that do not depend on the receiver (oracle J_or per rate, the counter trajectory, N_eval) are taken from
# the L1 raw file of the same channel and SNR, and N_eval is checked against the board's own counter on every run.
# Output: results/confirm/board_<channel>_<snr>_<build>_raw.npz in the same key layout as the L1 raw files, so that the mid-term
# analysis (sweep_analyse.analyse) runs on it unchanged.  A live window shows the tracking curves while the sweep runs.
#
#   python board_midterm_sweep.py primary 16 [--seeds 100] [--no-plot]
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, os.path.join(HERE, "..", "..", "sim"))
import numpy as np
import l2_ref as R
import run_board
from run_board import Board, find_port

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MID = os.path.join(REPO, "midterm_mtr-22", "2_code_and_results_by_phase")
L1RES = os.path.join(MID, "05_P3-P4_boundary_and_optimum_step", "results")
OUT = os.path.join(HERE, "..", "results", "confirm")
S_LIST = [5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1]
P_FPGA = [5, 6, 7, 8, 9, 10, 11]
CH = {"primary": ((40, 116), [40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 116]),
      "control": ((26, 77), [26, 34, 42, 50, 58, 66, 74, 77])}
N_T, BASE = 30000, 152000


def main():
    global P_FPGA
    ap = argparse.ArgumentParser()
    ap.add_argument("channel", choices=list(CH)); ap.add_argument("snr", type=float)
    ap.add_argument("--seeds", type=int, default=100); ap.add_argument("--port"); ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--ber14", action="store_true", help="the mid-term 14 dB BER-resolution study (E-5): primary channel, 14 dB, "
                    "mu 2^-7..2^-11, 1500 seeds 100000-101499, L1 reference final_primary_14_ber14_raw.npz")
    ap.add_argument("--baud", type=int, default=1_000_000, help="115200 for the version-1 bitstreams (e.g. the 26-bit build of 6 Nov)")
    a = ap.parse_args()
    (lo, hi), nodes = CH[a.channel]; snr = a.snr; tag_snr = f"{snr:.0f}"
    if a.ber14:
        assert a.channel == "primary" and snr == 14.0, "--ber14 is defined for the primary channel at 14 dB"
        P_FPGA = [7, 8, 9, 10, 11]
        seeds = list(range(100000, 100000 + (a.seeds if a.seeds != 100 else 1500)))
        L1 = np.load(os.path.join(L1RES, "final_primary_14_ber14_raw.npz"))
    else:
        seeds = list(range(2000, 2000 + a.seeds))
        L1 = np.load(os.path.join(L1RES, f"final_{a.channel}_{tag_snr}_raw.npz"))
    mu_L1 = list(L1["meta|mus"]); iL1 = [int(np.argmin([abs(m - 2.0 ** -p) for m in mu_L1])) for p in P_FPGA]

    run_board.BAUD = a.baud                                                   # Board.open() reads the module constant
    b = Board(a.port or find_port()); ident = b.ident()
    build = f"m{ident['B_MUL']}_a{ident['B_ACC']}_r{ident['RND']}"
    os.makedirs(OUT, exist_ok=True)
    stem = os.path.join(OUT, f"board_{a.channel}_{tag_snr}_{build}" + ("_ber14" if a.ber14 else ""))
    sq = R.ff.sigma_q_from_ebn0(snr)
    log = open(stem + "_run_log.txt", "a")
    def lg(s):
        print(s, flush=True); log.write(s + "\n"); log.flush()
    lg(f"board sweep {a.channel} {snr} dB, build {build} ({ident}), {len(seeds)} seeds {seeds[0]}-{seeds[-1]}, mu 2^-{P_FPGA}, "
       f"N_T {N_T}; start {time.ctime()}")

    # ---- live plot ----
    plot = not a.no_plot
    if plot:
        import matplotlib; matplotlib.use("TkAgg"); import matplotlib.pyplot as plt
        plt.ion()
        fig, ax = plt.subplots(1, 2, figsize=(14, 5.6))
        cm = plt.cm.viridis
        def draw(done):
            for x in ax: x.cla()
            for j, p in enumerate(P_FPGA):
                col = cm(j / (len(P_FPGA) - 1))
                Sx = [S for S in S_LIST if S in done]
                if Sx:
                    eb = [np.mean((done[S]["J3"][j] - done[S]["Jor"]) / done[S]["Jor"]) for S in Sx]
                    el = [np.mean((L1[f"{tag_snr}|{S}|J3"][iL1[j]] - L1[f"{tag_snr}|{S}|Jor"][0]) / L1[f"{tag_snr}|{S}|Jor"][0]) for S in Sx]
                    ax[0].loglog(Sx, eb, "o-", color=col, ms=4, label=f"board 2^-{p}")
                    ax[0].loglog(Sx, el, "--", color=col, lw=0.9)
            ax[0].plot([], [], "k--", lw=0.9, label="L1 float (mid-term), same grid")
            ax[0].invert_xaxis(); ax[0].set_xlabel("S (symbols per channel step; smaller = faster channel)")
            ax[0].set_ylabel("R3 excess MSE over the oracle, eps = (J3 - J_or) / J_or"); ax[0].legend(fontsize=7, ncol=2)
            ax[0].set_title("Tracking curves: board (solid) vs mid-term simulation (dashed)", fontsize=10)
            j8 = P_FPGA.index(8); Sx = [S for S in S_LIST if S in done]
            for key, col, nm in (("E1", "tab:red", "R1"), ("E2", "tab:orange", "R2"), ("E3", "tab:green", "R3")):
                if Sx:
                    n = np.array([done[S]["ne"] * len(seeds) for S in Sx], float)
                    kb = np.array([done[S][key][j8 if key != "E1" else 0].sum() for S in Sx], float)
                    kl = np.array([L1[f"{tag_snr}|{S}|{key}"][iL1[j8]].sum() for S in Sx], float)
                    nl = np.array([L1[f"{tag_snr}|{S}|n_eval"][0] * L1[f"{tag_snr}|{S}|{key}"].shape[1] for S in Sx], float)
                    ax[1].loglog(Sx, np.where(kb > 0, kb / n, np.nan), "o-", color=col, ms=4, label=f"{nm} board")
                    ax[1].loglog(Sx, np.where(kl > 0, kl / nl, np.nan), "--", color=col, lw=0.9, label=f"{nm} L1")
            ax[1].invert_xaxis(); ax[1].set_xlabel("S (smaller = faster channel)"); ax[1].set_ylabel("BER")
            ax[1].set_title("BER at mu = 2^-8: board (solid) vs mid-term simulation (dashed)", fontsize=10); ax[1].legend(fontsize=7, ncol=3)
            fig.suptitle(f"Boolean Board, {a.channel} channel, {snr:g} dB, build {build}, {len(seeds)} seeds  "
                         f"[{len(done)}/{len(S_LIST)} rates done]", fontsize=10)
            fig.tight_layout(); fig.canvas.draw_idle(); plt.pause(0.05)

    RAW, done, t0, nrun = {}, {}, time.time(), 0
    ckpt = stem + "_partial.npz"            # checkpoint after every point: an interrupted sweep resumes where it stopped
    if os.path.exists(ckpt):
        with np.load(ckpt) as P0:            # closed again at once (Windows cannot delete an open file)
            RAW = {k: P0[k] for k in P0.files}
        lg(f"  resuming from {os.path.basename(ckpt)}: {sum(k.endswith('|J3') for k in RAW)} points already measured")
    states = {s: R.ff.lfsr_start_values(s + 500000) for s in seeds}

    def point(S, c_lo, c_hi, ne):
        nonlocal nrun
        o = {k: np.zeros((len(P_FPGA), len(seeds))) for k in ("J2", "J3")}
        for k in ("E1", "E2", "E3", "ST", "UP"):
            o[k] = np.zeros((len(P_FPGA), len(seeds)), np.int64)
        for k, s in enumerate(seeds):
            for j, p in enumerate(P_FPGA):
                rep, _ = b.run(p, S, c_lo, c_hi, sq, N_T, N_T + ne, s, states[s]); nrun += 1
                c = rep["counters"]
                if c[0] != ne:
                    raise RuntimeError(f"board evaluated {c[0]} symbols, expected {ne} (S={S}, seed {s}, p {p})")
                o["E1"][j, k], o["E2"][j, k], o["E3"][j, k] = c[1], c[2], c[3]
                o["J2"][j, k], o["J3"][j, k] = c[4] / ne / 2 ** 24, c[5] / ne / 2 ** 24
                o["ST"][j, k], o["UP"][j, k] = c[6], c[7]
        return o

    for S in S_LIST + [None]:
        key = f"{tag_snr}|{S}"
        ne = int(L1[key + "|n_eval"][0])
        if key + "|J3" in RAW:
            if S is not None:
                done[S] = dict({k: RAW[f"{key}|{k}"] for k in ("J2", "J3", "E1", "E2", "E3")}, Jor=float(RAW[key + "|Jor"][0]), ne=ne)
            continue
        if S is not None:            # the board's counter trajectory must be the L1 one (checked in software, same rule as var_ctrl)
            cw = R.triangle_counter(N_T + ne, N_T, lo, hi, S)[N_T:]
            assert np.array_equal(cw, L1[key + "|c_win"].astype(int)), f"trajectory differs at S={S}"
        o = point(S, lo, hi, ne)
        for k, v in o.items():
            RAW[f"{key}|{k}"] = v
        RAW[key + "|Jor"] = L1[key + "|Jor"]; RAW[key + "|c_win"] = L1[key + "|c_win"]; RAW[key + "|n_eval"] = np.array([ne])
        RAW[key + "|n_bits"] = np.array([ne])
        np.savez_compressed(ckpt, **RAW)
        done[S] = dict(o, Jor=float(L1[key + "|Jor"][0]), ne=ne) if S is not None else None
        if S is None: done.pop(None)
        j8 = P_FPGA.index(8)
        lg(f"  {key:10s} N_eval {ne:7d}  mu=2^-8: J3 board {o['J3'][j8].mean():.5f} L1 {L1[key + '|J3'][iL1[j8]].mean():.5f}  "
           f"err R1/R2/R3 {o['E1'][j8].sum()}/{o['E2'][j8].sum()}/{o['E3'][j8].sum()}  [{time.time() - t0:.0f}s, {nrun} runs]")
        if plot and S is not None:
            draw(done)
    for cc in nodes:
        if f"{tag_snr}|static_c{cc}|J3" in RAW:
            continue
        o = point(None, cc, cc, BASE)
        for k, v in o.items():
            RAW[f"{tag_snr}|static_c{cc}|{k}"] = v
        RAW[f"{tag_snr}|static_c{cc}|bits"] = np.array([len(seeds) * BASE])
        np.savez_compressed(ckpt, **RAW)
        lg(f"  static c={cc:3d}: mu=2^-8 J3 {o['J3'][P_FPGA.index(8)].mean():.5f}  [{time.time() - t0:.0f}s]")
    RAW["meta|seeds"] = np.array(seeds); RAW["meta|static_seeds"] = np.array(seeds)
    RAW["meta|mus"] = np.array([2.0 ** -p for p in P_FPGA]); RAW["meta|S_list"] = np.array(S_LIST)
    RAW["meta|static_c"] = np.array(nodes); RAW["meta|channel"] = np.array([lo, hi]); RAW["meta|n_t"] = np.array([N_T])
    RAW["meta|paired"] = np.array([True])
    np.savez_compressed(stem + "_raw.npz", **RAW)
    if os.path.exists(ckpt):
        os.remove(ckpt)
    json.dump(dict(level="L5 (Boolean Board), supervised LMS, LFSR sum-of-uniforms noise", channel=a.channel, snr=snr, build=ident,
                   seeds=[seeds[0], seeds[-1]], mus=[f"2^-{p}" for p in P_FPGA], n_t=N_T, runs=nrun, seconds=round(time.time() - t0),
                   date=time.strftime("%Y-%m-%d %H:%M")), open(stem + "_config.json", "w"), indent=1)
    lg(f"done {time.ctime()}: {nrun} runs in {time.time() - t0:.0f} s -> {stem}_raw.npz")
    if plot:
        fig.savefig(stem + "_live.png", dpi=120)
        plt.ioff(); plt.show(block=False); plt.pause(2)


if __name__ == "__main__":
    main()
