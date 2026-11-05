# run_chain_syn_tests.py -- bit-exact regression of fpga/rtl/rx_chain_syn.v against the L2 chain (l2_ref.chain).  Level L3.
# Cases A-G are the seven cases of 09_P7-P8_RTL/code/run_chain_tests.py (same seeds, same payload generator); the H-M cases add
# the 26-bit accumulator, the ends of the FPGA mu range, the real N_T = 30000 and the board payload LFSR.
# Checks: every per-symbol signal (r_q d_q ya yf ea ef) and every counter identical; no symbol-overlap message.
# Responsible member: Aniket Mohapatra (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
# Usage (from fpga/sim):  python run_chain_syn_tests.py
import os, subprocess, sys
import l2_ref as R
import numpy as np

RTL_DIR = os.path.join(R.REPO, "fpga", "rtl")
MID_RTL = os.path.join(R.PKG, "09_P7-P8_RTL", "code")
SOURCES = [os.path.join(R.HERE, "tb_chain_syn.v")] + [os.path.join(RTL_DIR, f) for f in
           ("rx_chain_syn.v", "lms_rx_syn.v", "chan_front_syn.v", "var_ctrl_syn.v")] + \
          [os.path.join(MID_RTL, f) for f in ("lfsr_noise.v", "prbs15.v")]
LOG = os.path.join(R.HERE, "results", "chain_syn_test_log.txt")

# name, B_ACC, B_MUL, RND, P, S (None = static), c_lo, c_hi, ebn0, seed, NSYM, NT, payload ("np" = make_bits, "lfsr" = board LFSR)
CASES = [
    ("A_16_12_nearest_mu2-8_S20",     16, 12, 1, 8,  20,   40, 116, 14.0, 3001, 6000, 1500, "np"),
    ("B_12_12_trunc_mu2-8_S20",       12, 12, 0, 8,  20,   40, 116, 14.0, 3002, 6000, 1500, "np"),
    ("C_10_10_nearest_mu2-10_S28",    10, 10, 1, 10, 28,   40, 116, 14.0, 3003, 6000, 1500, "np"),
    ("D_static_16_12_mu2-8",          16, 12, 1, 8,  None, 40, 116, 14.0, 3004, 6000, 1500, "np"),
    ("E_stress_12_12_mu2-2_S5",       12, 12, 1, 2,  5,    40, 116, 10.0, 3005, 6000, 1500, "np"),
    ("F_fast_16_12_mu2-6_S1",         16, 12, 1, 6,  1,    40, 116, 14.0, 3006, 6000, 1500, "np"),
    ("G_control_ch_14_12_mu2-8_S50",  14, 12, 1, 8,  50,   26, 77,  16.0, 3007, 6000, 1500, "np"),
    ("H_26_12_nearest_mu2-8_S28",     26, 12, 1, 8,  28,   40, 116, 12.0, 3008, 6000, 1500, "np"),
    ("I_16_12_mu2-5_S10",             16, 12, 1, 5,  10,   40, 116, 10.0, 3009, 6000, 1500, "lfsr"),
    ("J_16_12_mu2-11_S224",           16, 12, 1, 11, 224,  40, 116, 10.0, 3010, 6000, 1500, "lfsr"),
    ("K_16_8_mu2-7_S56",              16, 8,  1, 7,  56,   40, 116, 12.0, 3011, 6000, 1500, "lfsr"),
    ("L_long_NT30000_16_12_mu2-8_S28", 16, 12, 1, 8, 28,   40, 116, 10.0, 3012, 40000, 30000, "lfsr"),
    ("M_32_16_mu2-5_S5",              32, 16, 1, 5,  5,    40, 116, 10.0, 3013, 6000, 1500, "lfsr"),
]


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    out, ok_all = [], True
    for (name, ba, bm, rnd, p, S, clo, chi, eb, seed, nsym, nt, pay) in CASES:
        d = os.path.join(R.HERE, "build", "vec_chain", name); os.makedirs(d, exist_ok=True)
        payload = R.make_bits(nsym - nt, seed) if pay == "np" else R.payload_bits(nsym - nt, seed)
        states = R.ff.lfsr_start_values(seed + 500000)
        sq = R.ff.sigma_q_from_ebn0(eb)
        bits, gold, gcount = R.chain(nsym, nt, ba, bm, rnd, p, S, clo, chi, sq, states, payload)
        with open(os.path.join(d, "seeds.hex"), "w") as f:
            for s_ in states: f.write("%09x\n" % s_)
        with open(os.path.join(d, "bits.hex"), "w") as f:
            for b in bits: f.write("%d\n" % b)
        vvp = os.path.join(d, "sim.vvp")
        dv = d.replace("\\", "/")
        cmd = ["iverilog", "-g2012", "-o", vvp] + [f"-Ptb_chain_syn.{k}={v}" for k, v in
               dict(NSYM=nsym, NT=nt, B_MUL=bm, B_ACC=ba, P=p, RND=rnd, C_LO=clo, C_HI=chi, SVAL=1 if S is None else S,
                    SIGQ=sq, STATIC=1 if S is None else 0).items()] + [f'-Ptb_chain_syn.DIR="{dv}"'] + SOURCES
        r1 = subprocess.run(cmd, capture_output=True, text=True)
        if r1.returncode != 0:
            msg = f"{name} COMPILE ERROR {r1.stderr[:800]}"; print(msg); out.append(msg); ok_all = False; continue
        r2 = subprocess.run(["vvp", vvp], capture_output=True, text=True)
        overlap = "ERROR" in r2.stdout
        lines = open(os.path.join(d, "out_chain.txt")).read().strip().splitlines()
        rcount = [int(v) for v in lines[-1].split()[1:]]
        rtl = np.array([[int(v) for v in ln.split()] for ln in lines[:-1]], dtype=np.int64)
        same = rtl.shape == gold.shape and np.array_equal(rtl, gold)
        nbad = int(np.sum(np.any(rtl != gold, axis=1))) if rtl.shape == gold.shape else -1
        cok = rcount == gcount
        ok = same and cok and not overlap
        ok_all &= ok
        msg = (f"{name:32s} per-symbol identical: {same} (differing {nbad}/{nsym}) | counters identical: {cok} | overlap: {overlap}\n"
               f"      L2 : n={gcount[0]} err R1/R2/R3 = {gcount[1]}/{gcount[2]}/{gcount[3]}  sse2={gcount[4]} sse3={gcount[5]} "
               f"stalls={gcount[6]} updates={gcount[7]}")
        if not cok: msg += f"\n      RTL: {rcount}"
        print(msg); out.append(msg)
    out.append("ALL PASS" if ok_all else "SOME FAIL"); print(out[-1])
    with open(LOG, "w") as fh:
        fh.write("# rx_chain_syn.v vs L2 chain (l2_ref.chain), iverilog, level L3\n" + "\n".join(out) + "\n")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
