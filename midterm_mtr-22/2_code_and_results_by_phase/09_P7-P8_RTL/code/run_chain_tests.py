# run_chain_tests.py -- full chain (PRBS, variation controller, noise, integer front end, R1/R2/R3, counters): L2 integer model vs RTL (iverilog).
import sys, os, subprocess
sys.path.insert(0, '..')
import numpy as np
from lms_lib import make_bits, lfsr_bits, triangle_counter
from fxp_lib import fxp_receivers
import fxp_front as ff
from config import CFG

L = 16
# name, B_ACC, B_MUL, RND, P, S (None = static), c_lo, c_hi, ebn0, seed, NSYM, NT
CASES = [
    ("A_16_12_nearest_mu2-8_S20",  16, 12, 1, 8, 20, 40, 116, 14.0, 3001, 6000, 1500),
    ("B_12_12_trunc_mu2-8_S20",    12, 12, 0, 8, 20, 40, 116, 14.0, 3002, 6000, 1500),
    ("C_10_10_nearest_mu2-10_S28", 10, 10, 1, 10, 28, 40, 116, 14.0, 3003, 6000, 1500),
    ("D_static_16_12_mu2-8",       16, 12, 1, 8, None, 40, 116, 14.0, 3004, 6000, 1500),
    ("E_stress_12_12_mu2-2_S5",    12, 12, 1, 2, 5, 40, 116, 10.0, 3005, 6000, 1500),
    ("F_fast_16_12_mu2-6_S1",      16, 12, 1, 6, 1, 40, 116, 14.0, 3006, 6000, 1500),
    ("G_control_ch_14_12_mu2-8_S50", 14, 12, 1, 8, 50, 26, 77, 16.0, 3007, 6000, 1500),
]

ok_all = True
for (name, ba, bm, rnd, p, S, clo, chi, eb, seed, nsym, nt) in CASES:
    d = os.path.join("vec", "chain_" + name); os.makedirs(d, exist_ok=True)
    # --- L2 integer model
    tr = lfsr_bits(nt, CFG["prbs_nbits"], CFG["prbs_taps"], CFG["prbs_seed"])
    pay = make_bits(nsym - nt, seed)
    bits = np.concatenate([tr, pay]).astype(np.int64)
    c = triangle_counter(nsym, nt, clo, chi, S)
    states = ff.lfsr_start_values(seed + 500000)
    noise = ff.noise_int_stream(nsym, states)
    sq = ff.sigma_q_from_ebn0(eb)
    rq, dq = ff.front_end_int(bits, c, noise, sq)
    yA, yF, eA, eF, wH, stalls, updates = fxp_receivers(rq, dq, L, p, nt, bm, ba, rnd, 10 ** 9)
    gold = np.stack([rq, dq, yA, yF, eA, eF], axis=1)
    w = np.arange(nt, nsym)
    n_eval = len(w)
    e1 = int(np.sum((rq[w] >= 0).astype(int) != bits[w]))
    e2 = int(np.sum((yF[w] >= 0).astype(int) != bits[w - 2]))
    e3 = int(np.sum((yA[w] >= 0).astype(int) != bits[w - 2]))
    sse2 = int(np.sum(eF[w].astype(object) ** 2)); sse3 = int(np.sum(eA[w].astype(object) ** 2))
    gcount = [n_eval, e1, e2, e3, sse2, sse3, int(stalls), int(updates)]
    # --- files for the testbench
    with open(os.path.join(d, "seeds.hex"), "w") as f:
        for s_ in states: f.write("%09x\n" % s_)
    with open(os.path.join(d, "bits.hex"), "w") as f:
        for b in bits: f.write("%d\n" % b)
    vvp = os.path.join(d, "sim.vvp")
    cmd = ["iverilog", "-g2012", "-o", vvp, f"-Ptb_chain.NSYM={nsym}", f"-Ptb_chain.NT={nt}", f"-Ptb_chain.B_MUL={bm}", f"-Ptb_chain.B_ACC={ba}",
           f"-Ptb_chain.P={p}", f"-Ptb_chain.RND={rnd}", f"-Ptb_chain.C_LO={clo}", f"-Ptb_chain.C_HI={chi}", f"-Ptb_chain.SVAL={1 if S is None else S}",
           f"-Ptb_chain.SIGQ={sq}", f"-Ptb_chain.STATIC={1 if S is None else 0}", f"-Ptb_chain.DIR=\"{d}\"",
           "tb_chain.v", "rx_chain.v", "lfsr_noise.v", "prbs15.v", "var_ctrl.v", "chan_front.v", "lms_rx.v"]
    r1 = subprocess.run(cmd, capture_output=True, text=True)
    if r1.returncode != 0:
        print(name, "COMPILE ERROR", r1.stderr[:800]); ok_all = False; continue
    subprocess.run(["vvp", vvp], capture_output=True, text=True)
    lines = open(os.path.join(d, "out_chain.txt")).read().strip().splitlines()
    rcount = [int(v) for v in lines[-1].split()[1:]]
    rtl = np.array([[int(v) for v in ln.split()] for ln in lines[:-1]], dtype=np.int64)
    same = rtl.shape == gold.shape and np.array_equal(rtl, gold)
    nbad = int(np.sum(np.any(rtl != gold, axis=1))) if rtl.shape == gold.shape else -1
    cok = rcount == gcount
    ok_all &= bool(same and cok)
    print(f"{name:32s} per-symbol identical: {same} (differing {nbad}/{nsym}) | counters identical: {cok}")
    print(f"      L2 : n={gcount[0]} err R1/R2/R3 = {gcount[1]}/{gcount[2]}/{gcount[3]}  sse2={gcount[4]} sse3={gcount[5]} stalls={gcount[6]} updates={gcount[7]}")
    if not cok: print(f"      RTL: {rcount}")
print("ALL PASS" if ok_all else "SOME FAIL")
