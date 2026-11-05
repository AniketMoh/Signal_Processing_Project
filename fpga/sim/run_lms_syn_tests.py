# run_lms_syn_tests.py -- bit-exact regression of fpga/rtl/lms_rx_syn.v against the L2 model (fxp_lib.fxp_receivers).  Level L3.
# Responsible member: Pradeep Kumar (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
# Golden vectors are generated exactly as in 09_P7-P8_RTL/code/run_rx_tests.py (same L2 functions, unchanged); the L2 model is
# imported from a runnable copy of the mid-term package, built once in fpga/sim/build/ from its manifest.csv.
# Checks per case: every per-symbol output (ya, yf, ea, ef) identical, stall and update counters identical, and the cycle-budget
# check in lms_rx_syn silent.  A negative control (symbols 9 clocks apart) must trip the cycle-budget check.
#
# Usage (from fpga/sim):  python run_lms_syn_tests.py          needs numpy, numba, iverilog on PATH
import csv, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PKG = os.path.join(REPO, "midterm_mtr-22", "2_code_and_results_by_phase")
BUILD = os.path.join(HERE, "build")
MODEL = os.path.join(BUILD, "runnable_code")
RTL = os.path.join(REPO, "fpga", "rtl", "lms_rx_syn.v")
TB = os.path.join(HERE, "tb_lms_rx_syn.v")
LOG = os.path.join(HERE, "results", "lms_syn_test_log.txt")


def build_model_copy():
    if os.path.isfile(os.path.join(MODEL, "fxp_lib.py")):
        return
    with open(os.path.join(PKG, "manifest.csv")) as fh:
        for row in csv.DictReader(fh):
            dst = os.path.join(MODEL, row["original_path_in_runnable_layout"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(PKG, row["location_in_this_package"]), dst)


build_model_copy()
sys.path.insert(0, MODEL)
import numpy as np
from lms_lib import make_experiment, delayed_symbols, apply_channel
from fxp_lib import fxp_receivers, quantize_signal, lfsr_noise

L = 16; DELTA = 2
# name, B_ACC, B_MUL, RND, P, S, ebn0, noise, seed, NSYM, NT, SPACING, expect_budget_error
CASES = [
    # the five cases of run_rx_tests.py (mid-term, 09_P7-P8_RTL)
    ("typical_16_12_nearest_mu2-8",   16, 12, 1, 8,  20,  14.0, "gauss", 2001, 4000, 1500, 16, False),
    ("stalls_12_12_trunc_mu2-8",      12, 12, 0, 8,  20,  14.0, "gauss", 2002, 4000, 1500, 16, False),
    ("narrow_10_10_nearest_mu2-10",   10, 10, 1, 10, 28,  14.0, "gauss", 2003, 4000, 1500, 16, False),
    ("wide_26_12_nearest_mu2-8",      26, 12, 1, 8,  20,  14.0, "lfsr",  2004, 4000, 1500, 16, False),
    ("saturation_stress_12_12_mu2-2", 12, 12, 1, 2,  5,   10.0, "lfsr",  2005, 4000, 1500, 16, False),
    # new: word-length sweep corners, the FPGA mu range, truncation at the default width, left-shift update path
    ("acc26_mul8_mu2-8",              26, 8,  1, 8,  20,  14.0, "lfsr",  2101, 4000, 1500, 16, False),
    ("acc26_mul16_mu2-8",             26, 16, 1, 8,  20,  14.0, "lfsr",  2102, 4000, 1500, 16, False),
    ("acc32_mul12_mu2-5_leftshift",   32, 12, 1, 5,  10,  14.0, "lfsr",  2103, 4000, 1500, 16, False),
    ("acc16_mul12_mu2-5",             16, 12, 1, 5,  10,  14.0, "lfsr",  2104, 4000, 1500, 16, False),
    ("acc16_mul12_mu2-11",            16, 12, 1, 11, 224, 14.0, "lfsr",  2105, 4000, 1500, 16, False),
    ("acc16_mul12_trunc_mu2-8",       16, 12, 0, 8,  20,  14.0, "lfsr",  2106, 4000, 1500, 16, False),
    ("acc16_mul8_mu2-7_16dB",         16, 8,  1, 7,  28,  16.0, "lfsr",  2107, 4000, 1500, 16, False),
    # new: real training length N_T = 30000 (freeze at the true instant)
    ("long_NT30000_16_12_mu2-8",      16, 12, 1, 8,  20,  14.0, "lfsr",  2108, 34000, 30000, 16, False),
    # cycle budget: minimum spacing passes, one clock less must be flagged (negative control)
    ("budget_min_spacing10",          16, 12, 1, 8,  20,  14.0, "lfsr",  2001, 4000, 1500, 10, False),
    ("budget_negative_spacing9",      16, 12, 1, 8,  20,  14.0, "lfsr",  2001, 4000, 1500, 9,  True),
]


def make_case(S, ebn0, noise, seed, nsym, nt):
    ex = make_experiment(S, (40, 116), ebn0, seed, N_T=nt, N_eval=nsym - nt)
    if noise == "lfsr":
        ex["r"] = apply_channel(ex["x"], ex["taps"]) + lfsr_noise(len(ex["x"]), ex["sigma"], seed + 500000)
    d = delayed_symbols(ex["x"], DELTA)
    return quantize_signal(ex["r"]), quantize_signal(d)


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    lines_out, ok_all = [], True
    for (name, ba, bm, rnd, p, S, eb, noise, seed, nsym, nt, spacing, expect_err) in CASES:
        d = os.path.join(BUILD, "vec", name); os.makedirs(d, exist_ok=True)
        rq, dq = make_case(S, eb, noise, seed, nsym, nt)
        np.savetxt(os.path.join(d, "r.txt"), rq, fmt="%d"); np.savetxt(os.path.join(d, "d.txt"), dq, fmt="%d")
        yA, yF, eA, eF, wH, stalls, updates = fxp_receivers(rq, dq, L, p, nt, bm, ba, rnd, 10 ** 9)
        gold = np.stack([yA, yF, eA, eF], axis=1)
        vvp = os.path.join(d, "sim.vvp")
        dir_v = d.replace("\\", "/")
        cmd = ["iverilog", "-g2012", "-o", vvp, f"-Ptb_lms_rx_syn.NSYM={nsym}", f"-Ptb_lms_rx_syn.NT={nt}",
               f"-Ptb_lms_rx_syn.B_MUL={bm}", f"-Ptb_lms_rx_syn.B_ACC={ba}", f"-Ptb_lms_rx_syn.P={p}",
               f"-Ptb_lms_rx_syn.RND={rnd}", f"-Ptb_lms_rx_syn.SPACING={spacing}", f"-Ptb_lms_rx_syn.DIR=\"{dir_v}\"", TB, RTL]
        r1 = subprocess.run(cmd, capture_output=True, text=True)
        if r1.returncode != 0:
            msg = f"{name:32s} COMPILE ERROR {r1.stderr[:500]}"
            print(msg); lines_out.append(msg); ok_all = False; continue
        r2 = subprocess.run(["vvp", vvp], capture_output=True, text=True)
        budget_err = "ERROR lms_rx_syn" in r2.stdout
        txt = open(os.path.join(d, "out_rtl.txt")).read().strip().splitlines()
        cnt = txt[-1].split()
        rtl = np.array([[int(v) for v in ln.split()] for ln in txt[:-1]], dtype=np.int64)
        same = rtl.shape == gold.shape and np.array_equal(rtl, gold)
        nbad = int(np.sum(np.any(rtl != gold, axis=1))) if rtl.shape == gold.shape else -1
        c_ok = (int(cnt[1]) == stalls and int(cnt[2]) == updates)
        if expect_err:
            ok = budget_err
            msg = (f"{name:32s} negative control: cycle-budget error reported: {budget_err} "
                   f"(outputs identical: {same}, differing {nbad} of {nsym}) -> {'PASS' if ok else 'FAIL'}")
        else:
            ok = same and c_ok and not budget_err
            msg = (f"{name:32s} outputs identical: {same} (differing {nbad} of {nsym}) | stalls RTL {cnt[1]} vs L2 {stalls}, "
                   f"updates RTL {cnt[2]} vs L2 {updates}: {c_ok} | budget error: {budget_err} | spacing {spacing}")
        print(msg); lines_out.append(msg); ok_all &= ok
    lines_out.append("ALL PASS" if ok_all else "SOME FAIL")
    print(lines_out[-1])
    with open(LOG, "w") as fh:
        fh.write("# lms_rx_syn.v vs fxp_lib.fxp_receivers (L2), iverilog, level L3\n")
        fh.write("\n".join(lines_out) + "\n")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
