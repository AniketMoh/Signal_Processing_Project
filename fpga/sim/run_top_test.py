# run_top_test.py -- end-to-end simulation of top_boolean: 'I', then two 'X' experiments over the UART model; the decoded
# reports must equal the L2 counters (l2_ref.chain with the payload LFSR) exactly.  Level L3.
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
# Usage (from fpga/sim):  python run_top_test.py
import os, subprocess, sys
import l2_ref as R
import protocol as P

RTL = os.path.join(R.REPO, "fpga", "rtl")
MID = os.path.join(R.PKG, "09_P7-P8_RTL", "code")
SRC = [os.path.join(R.HERE, "tb_top.v")] + [os.path.join(RTL, f) for f in (
    "top_boolean.v", "host_if.v", "uart_rx.v", "uart_tx.v", "board_io.v", "exp_core.v", "payload_lfsr.v", "payload_io.v", "fifo_sync.v",
    "rx_chain_syn.v", "lms_rx_syn.v", "chan_front_syn.v", "var_ctrl_syn.v")] + [os.path.join(MID, f) for f in ("lfsr_noise.v", "prbs15.v")]
LOG = os.path.join(R.HERE, "results", "top_test_log.txt")

# p, S (None = static), c_lo, c_hi, ebn0, noise seed, payload seed, NT, NSYM
RUNS = [(8, 28, 40, 116, 10.0, 4001, 777, 1500, 5000),
        (5, None, 26, 77, 8.0, 4002, 0, 1000, 3000)]


def main():
    d = os.path.join(R.HERE, "build", "top"); os.makedirs(d, exist_ok=True)
    groups, expect = [], []
    groups.append(([ord("I")], 8))
    total = 8
    for (p, S, clo, chi, eb, ns, ps, nt, nsym) in RUNS:
        states = R.ff.lfsr_start_values(ns + 500000)
        sq = R.ff.sigma_q_from_ebn0(eb)
        fr = P.config_frame(p, S, clo, chi, S is None, sq, nt, nsym, ps, states)
        total += P.REPORT_LEN
        groups.append((list(fr), total))
        _, _, cnt = R.chain(nsym, nt, 16, 12, 1, p, S, clo, chi, sq, states, R.payload_bits(nsym - nt, ps))
        expect.append((nsym, cnt))
    with open(os.path.join(d, "cmds.txt"), "w") as f:
        for (bs, w) in groups:
            f.write(f"{len(bs)} {w} " + " ".join(str(x) for x in bs) + "\n")
    vvp = os.path.join(d, "sim.vvp")
    dv = d.replace("\\", "/")
    r = subprocess.run(["iverilog", "-g2012", "-o", vvp, f'-Ptb_top.DIR="{dv}"'] + SRC, capture_output=True, text=True)
    if r.returncode != 0:
        print("COMPILE ERROR", r.stderr[:1500]); return 1
    r = subprocess.run(["vvp", vvp], capture_output=True, text=True)
    errs = [ln for ln in r.stdout.splitlines() if "ERROR" in ln]
    rx = [int(x) for x in open(os.path.join(d, "rx.txt")).read().split()]
    lines, ok = [], not errs
    try:
        ident = P.parse_ident(rx[:8]); lines.append(f"identification: {ident}")
        ok &= ident["B_MUL"] == 12 and ident["B_ACC"] == 16 and ident["RND"] == 1
        for i, (nsym, cnt) in enumerate(expect):
            rep = P.parse_report(rx[8 + 48 * i: 8 + 48 * (i + 1)])
            same = rep["counters"] == cnt and rep["sym_idx"] == nsym and rep["done"] and rep["host"]
            ok &= same
            lines.append(f"run {i}: board-model report identical to L2: {same} | report {rep} | L2 {cnt}")
    except (ValueError, IndexError) as e:
        ok = False; lines.append(f"decode error: {e}; received {len(rx)} bytes")
    if errs: lines.append("simulation errors: " + "; ".join(errs[:5]))
    lines.append("ALL PASS" if ok else "SOME FAIL")
    print("\n".join(lines))
    with open(LOG, "w") as fh:
        fh.write("# top_boolean (UART protocol, exp_core, payload LFSR) vs L2, iverilog, level L3\n" + "\n".join(lines) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
