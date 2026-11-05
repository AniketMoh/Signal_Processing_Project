"""P3 pilot, heavy part: continuous triangular variation, R1/R2/R3 on identical data.  L1, supervised LMS, pilot seeds 1000-1019.
Stores per-seed raw numbers in results/p3_raw.npz; analysis is in p3_analyse.py.  Run: python3 p3_run.py > results/p3_run_log.txt"""
import time, numpy as np
from exp_lib import *

CHANNELS = {"control": (26, 77), "candidate_A": (64, 115), "primary": (40, 116)}
SNRS = [14.0, 16.0]
S_GRID = [1000, 500, 200, 100, 50, 20, 10, 5, 2, 1]
MUS = [2.0 ** -k for k in (6, 7, 8, 9, 10)]
SEEDS = list(range(1000, 1020))
STATIC_SEEDS = list(range(1000, 1020))
N_T, N_EVAL = CFG["N_T"], CFG["N_eval"]; N_TOT = N_T + N_EVAL
RAW = {}


def one_point(c, snr, seeds, mus):
    """returns arrays [mu, seed] of J2, J3 and error counts e1, e2, e3 over the evaluation window"""
    J2 = np.zeros((len(mus), len(seeds))); J3 = np.zeros_like(J2)
    E1 = np.zeros((len(mus), len(seeds)), np.int64); E2 = np.zeros_like(E1); E3 = np.zeros_like(E1)
    for k, seed in enumerate(seeds):
        ex = make_exp_from_counter(c, N_T, snr, seed)
        for i, mu in enumerate(mus):
            yA, yF, eA, eF, _ = run_lms(ex, mu, 10 ** 9)
            J3[i, k] = np.mean(eA[N_T:] ** 2); J2[i, k] = np.mean(eF[N_T:] ** 2)
            i1, i2, i3 = ber_indicators(ex, yA, yF)
            E1[i, k] = i1[N_T:].sum(); E2[i, k] = i2[N_T:].sum(); E3[i, k] = i3[N_T:].sum()
    return J2, J3, E1, E2, E3


def main():
    t0 = time.time()
    print(f"P3 pilot run: channels {CHANNELS}, SNR {SNRS}, S grid {S_GRID}, mu 2^-6..2^-10, seeds {SEEDS[0]}-{SEEDS[-1]}, N_T={N_T}, N_eval={N_EVAL}")
    for ch, (lo, hi) in CHANNELS.items():
        for snr in SNRS:
            s2 = sigma_from_ebn0(snr) ** 2
            # --- continuous variation points (S) and the literal static S0 point (S = None)
            for S in S_GRID + [None]:
                c = triangle_counter(N_TOT, N_T, lo, hi, S)
                taps = taps_from_counter(c, H2)
                Jor = float(np.mean(oracle_J_series(taps, N_T, N_TOT, s2)))
                J2, J3, E1, E2, E3 = one_point(c, snr, SEEDS, MUS)
                key = f"{ch}|{snr:.0f}|{S}"
                RAW[key + "|J2"] = J2; RAW[key + "|J3"] = J3; RAW[key + "|E1"] = E1; RAW[key + "|E2"] = E2; RAW[key + "|E3"] = E3
                RAW[key + "|Jor"] = np.array([Jor]); RAW[key + "|c_win"] = c[N_T:].astype(np.int16)
                print(f"  {key:28s} Jor {Jor:.5f}  R3 MSE(mu=2^-8) {J3[2].mean():.5f}  R2 {J2[2].mean():.5f}  BER R1/R2/R3 {E1[2].sum()/(len(SEEDS)*N_EVAL):.2e}/{E2[2].sum()/(len(SEEDS)*N_EVAL):.2e}/{E3[2].sum()/(len(SEEDS)*N_EVAL):.2e}   [{time.time()-t0:.0f}s]", flush=True)
            # --- static runs on a c grid, for the trajectory-averaged static baseline
            cg = np.unique(np.round(np.linspace(lo, hi, 7)).astype(int))
            for cc in cg:
                c = np.full(N_TOT, cc, dtype=np.int64)
                J2, J3, E1, E2, E3 = one_point(c, snr, STATIC_SEEDS, MUS)
                RAW[f"{ch}|{snr:.0f}|static_c{cc}|J3"] = J3; RAW[f"{ch}|{snr:.0f}|static_c{cc}|E3"] = E3
            RAW[f"{ch}|{snr:.0f}|cgrid"] = cg
    np.savez_compressed("results/p3_raw.npz", **RAW)
    print(f"done in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main()
