"""Sweep engine for the tracking experiment (P3 pilot grids now, the final P4 sweep after FREEZE-1).  Level L1, supervised LMS.
The same code is used for pilot data (seeds 1000-1019, labelled L1 pilot) and for the final data (seeds 2000-2099) -- only the configuration differs.
The LMS loop is lms_lib.lms_receivers, unchanged.
Evaluation window rule (P-13 proposal): N_eval(S) = P * 2*(c_hi-c_lo)*S with P = max(1, round(152000 / (2*(c_hi-c_lo)*S))),
i.e. an integer number of FULL triangle periods, as close as possible to 152000 symbols and never less than one period."""
import time, numpy as np
from exp_lib import *


def n_eval_for(S, c_lo, c_hi, base=152000):
    if S is None:
        return base
    per = 2 * (c_hi - c_lo) * S
    return max(1, round(base / per)) * per


GAPS = (10, 20, 40)          # burst definition: errors closer than GAP symbols belong to one burst (E-1 sensitivity; 20 is the reference value)


def count_bursts(err, gap):
    """Number of error bursts in a 0/1 error indicator: consecutive errors less than `gap` symbols apart form one burst."""
    idx = np.flatnonzero(err)
    if len(idx) == 0:
        return 0
    return 1 + int(np.sum(np.diff(idx) > gap))


def run_point_full(c_arr, n_t, snr, seeds, mus):
    """Like run_point, but also returns burst counts (E-2).  All arrays are [mu, seed]; nothing about the LMS changes.
    Keys: J2, J3, E1, E2, E3 (error counts), B1_20, B2_20, B3_10, B3_20, B3_40 (burst counts), n_bits (bits per seed in the window)."""
    out = {k: np.zeros((len(mus), len(seeds))) for k in ("J2", "J3")}
    for k in ["E1", "E2", "E3", "B1_20", "B2_20"] + [f"B3_{g}" for g in GAPS]:
        out[k] = np.zeros((len(mus), len(seeds)), np.int64)
    for k, seed in enumerate(seeds):
        ex = make_exp_from_counter(c_arr, n_t, snr, seed)
        for i, mu in enumerate(mus):
            yA, yF, eA, eF, _ = run_lms(ex, mu, 10 ** 9)
            out["J3"][i, k] = np.mean(eA[n_t:] ** 2); out["J2"][i, k] = np.mean(eF[n_t:] ** 2)
            i1, i2, i3 = ber_indicators(ex, yA, yF)
            i1, i2, i3 = i1[n_t:], i2[n_t:], i3[n_t:]              # evaluation window only (training excluded)
            out["E1"][i, k] = i1.sum(); out["E2"][i, k] = i2.sum(); out["E3"][i, k] = i3.sum()
            out["B1_20"][i, k] = count_bursts(i1, 20); out["B2_20"][i, k] = count_bursts(i2, 20)
            for g in GAPS:
                out[f"B3_{g}"][i, k] = count_bursts(i3, g)
    out["n_bits"] = np.array([len(c_arr) - n_t])                     # bits per seed in the evaluation window
    return out


def run_point(c_arr, n_t, snr, seeds, mus):
    """Original interface (kept so that earlier scripts reproduce their results unchanged)."""
    o = run_point_full(c_arr, n_t, snr, seeds, mus)
    return o["J2"], o["J3"], o["E1"], o["E2"], o["E3"]


def run_sweep(cfg, out_npz, log=print):
    """cfg keys: channel=(lo,hi), snrs, S_list, mus, seeds, static_seeds, static_c, n_t, base_eval, static_ber_records (n_rec, rec_len, seed0) or None"""
    lo, hi = cfg["channel"]; n_t = cfg["n_t"]; RAW = {}; t0 = time.time()
    for snr in cfg["snrs"]:
        s2 = sigma_from_ebn0(snr) ** 2
        for S in cfg["S_list"] + [None]:
            ne = n_eval_for(S, lo, hi, cfg["base_eval"])
            c = triangle_counter(n_t + ne, n_t, lo, hi, S)
            Jor = float(np.mean(oracle_J_series(taps_from_counter(c, H2), n_t, n_t + ne, s2)))
            o = run_point_full(c, n_t, snr, cfg["seeds"], cfg["mus"])
            key = f"{snr:.0f}|{S}"
            for k, v in o.items():
                RAW[key + "|" + k] = v
            RAW[key + "|Jor"] = np.array([Jor]); RAW[key + "|c_win"] = c[n_t:].astype(np.int16); RAW[key + "|n_eval"] = np.array([ne])
            log(f"  {key:12s} N_eval {ne:7d}  Jor {Jor:.5f}   [{time.time()-t0:.0f}s]")
        # static baseline runs (measured LMS, NOT oracle) on the c grid; same seeds as the trajectory runs -> paired comparison (E-1)
        for cc in cfg["static_c"]:
            c = np.full(n_t + cfg["base_eval"], cc, dtype=np.int64)
            o = run_point_full(c, n_t, snr, cfg["static_seeds"], cfg["mus"])
            for k, v in o.items():
                RAW[f"{snr:.0f}|static_c{cc}|{k}"] = v
            RAW[f"{snr:.0f}|static_c{cc}|bits"] = np.array([len(cfg["static_seeds"]) * cfg["base_eval"]])
        log(f"  static baselines done for {snr:.0f} dB [{time.time()-t0:.0f}s]")
    # metadata needed for the paired analysis (E-2)
    RAW["meta|seeds"] = np.array(cfg["seeds"]); RAW["meta|static_seeds"] = np.array(cfg["static_seeds"])
    RAW["meta|mus"] = np.array(cfg["mus"]); RAW["meta|S_list"] = np.array(cfg["S_list"]); RAW["meta|static_c"] = np.array(cfg["static_c"])
    RAW["meta|channel"] = np.array(cfg["channel"]); RAW["meta|n_t"] = np.array([n_t]); RAW["meta|paired"] = np.array([list(cfg["seeds"]) == list(cfg["static_seeds"])])
    np.savez_compressed(out_npz, **RAW)
    return RAW
