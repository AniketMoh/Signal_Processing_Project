# run_rx_tests.py -- golden vectors from the L2 model (fxp_lib.fxp_receivers), RTL simulation with iverilog, bit-exact comparison.
# Each case: B_ACC, B_MUL, rounding, P (mu = 2^-P), channel / noise.  Integers in s16.12.
import sys, os, subprocess
sys.path.insert(0, '..')
import numpy as np
from lms_lib import make_experiment, delayed_symbols, apply_channel
from fxp_lib import fxp_receivers, quantize_signal, lfsr_noise

L = 16; DELTA = 2
CASES = [
    # name, B_ACC, B_MUL, RND, P, S, ebn0, noise, seed
    ("typical_16_12_nearest_mu2-8",   16, 12, 1, 8, 20, 14.0, "gauss", 2001),
    ("stalls_12_12_trunc_mu2-8",      12, 12, 0, 8, 20, 14.0, "gauss", 2002),
    ("narrow_10_10_nearest_mu2-10",   10, 10, 1, 10, 28, 14.0, "gauss", 2003),
    ("wide_26_12_nearest_mu2-8",      26, 12, 1, 8, 20, 14.0, "lfsr",  2004),
    ("saturation_stress_12_12_mu2-2", 12, 12, 1, 2, 5, 10.0, "lfsr",  2005),
]
NSYM, NT = 4000, 1500

def make_case(S, ebn0, noise, seed):
    ex = make_experiment(S, (40, 116), ebn0, seed, N_T=NT, N_eval=NSYM - NT)
    if noise == "lfsr":
        ex["r"] = apply_channel(ex["x"], ex["taps"]) + lfsr_noise(len(ex["x"]), ex["sigma"], seed + 500000)
    d = delayed_symbols(ex["x"], DELTA)
    return quantize_signal(ex["r"]), quantize_signal(d)

summary = []
for (name, ba, bm, rnd, p, S, eb, noise, seed) in CASES:
    d = os.path.join("vec", name); os.makedirs(d, exist_ok=True)
    rq, dq = make_case(S, eb, noise, seed)
    np.savetxt(os.path.join(d, "r.txt"), rq, fmt="%d"); np.savetxt(os.path.join(d, "d.txt"), dq, fmt="%d")
    yA, yF, eA, eF, wH, stalls, updates = fxp_receivers(rq, dq, L, p, NT, bm, ba, rnd, 10 ** 9)
    gold = np.stack([yA, yF, eA, eF], axis=1)
    # compile + run the RTL simulation
    vvp = os.path.join(d, "sim.vvp")
    cmd = ["iverilog", "-g2012", "-o", vvp, f"-Ptb_lms_rx.NSYM={NSYM}", f"-Ptb_lms_rx.NT={NT}", f"-Ptb_lms_rx.B_MUL={bm}",
           f"-Ptb_lms_rx.B_ACC={ba}", f"-Ptb_lms_rx.P={p}", f"-Ptb_lms_rx.RND={rnd}", f"-Ptb_lms_rx.DIR=\"{d}\"", "tb_lms_rx.v", "lms_rx.v"]
    r1 = subprocess.run(cmd, capture_output=True, text=True)
    if r1.returncode != 0:
        print(name, "COMPILE ERROR", r1.stderr[:500]); summary.append((name, False)); continue
    r2 = subprocess.run(["vvp", vvp], capture_output=True, text=True)
    lines = open(os.path.join(d, "out_rtl.txt")).read().strip().splitlines()
    cnt = lines[-1].split(); rtl = np.array([[int(v) for v in ln.split()] for ln in lines[:-1]], dtype=np.int64)
    same = rtl.shape == gold.shape and np.array_equal(rtl, gold)
    c_ok = (int(cnt[1]) == stalls and int(cnt[2]) == updates)
    nbad = int(np.sum(np.any(rtl != gold, axis=1))) if rtl.shape == gold.shape else -1
    sat_info = f"max|ya|={np.abs(yA).max()} max|eA|={np.abs(eA).max()}"
    print(f"{name:34s} outputs identical: {same}  (symbols differing: {nbad} of {NSYM}) | stall counter RTL {cnt[1]} vs L2 {stalls}, updates RTL {cnt[2]} vs L2 {updates}: {c_ok} | {sat_info}")
    summary.append((name, same and c_ok))
print("ALL PASS" if all(ok for _, ok in summary) else "SOME FAIL")
