# run_payload_test.py -- simulation of payload transport through top_boolean (L3): bytes from the "PC" are the payload, the
# board returns the delay-aligned decisions of R1, R2, R3 and a report; the PWM playback outputs the selected receiver.
# Checks against the L2 chain (l2_ref.chain with the same payload bits):
#   * every returned byte of R1, R2, R3 equals the L2 decisions, packed MSB first and aligned (R1 delay 0, R2/R3 delay 2);
#   * the report counters equal the L2 counters;
#   * the played samples are exactly the selected receiver's bytes, in order;
#   * the output-full pause was exercised (decision buffer of 8 words), and two payload runs follow each other correctly.
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
# Usage (from fpga/sim):  python run_payload_test.py
import os, subprocess, sys
import numpy as np
import l2_ref as R
import protocol as P

RTL = os.path.join(R.REPO, "fpga", "rtl")
MID = os.path.join(R.PKG, "09_P7-P8_RTL", "code")
SRC = [os.path.join(R.HERE, "tb_payload.v")] + [os.path.join(RTL, f) for f in (
    "top_boolean.v", "host_if.v", "uart_rx.v", "uart_tx.v", "board_io.v", "exp_core.v", "payload_lfsr.v", "payload_io.v",
    "fifo_sync.v", "rx_chain_syn.v", "lms_rx_syn.v", "chan_front_syn.v", "var_ctrl_syn.v")] + \
      [os.path.join(MID, f) for f in ("lfsr_noise.v", "prbs15.v")]
LOG = os.path.join(R.HERE, "results", "payload_test_log.txt")

# name, SW (play_sel in SW[11:10]), runs: (p, S, c_lo, c_hi, ebn0, noise seed, NT, n_bytes, play, data seed)
SIMS = [
    ("play_R3", 0x0000, [(8, 28, 40, 116, 8.0, 6001, 1000, 64, True, 1), (5, None, 40, 116, 10.0, 6002, 800, 40, False, 2)]),
    ("play_R1", 0x0800, [(8, 5, 40, 116, 6.0, 6003, 1000, 48, True, 3)]),
]


def expected(run):
    p, S, clo, chi, eb, ns, nt, nb, play, ds = run
    data = np.random.default_rng(ds).integers(0, 256, nb, dtype=np.uint8)
    pad = np.zeros(1, dtype=np.uint8)
    payload = np.unpackbits(np.concatenate([data, pad])).astype(np.int64)        # MSB first
    states = R.ff.lfsr_start_values(ns + 500000)
    sq = R.ff.sigma_q_from_ebn0(eb)
    ntot = P.payload_total(nt, nb)
    _, g, cnt = R.chain(ntot, nt, 16, 12, 1, p, S, clo, chi, sq, states, payload)
    rq, yA, yF = g[:, 0], g[:, 2], g[:, 3]
    pk = lambda v: np.packbits((v >= 0).astype(np.uint8)).tobytes()
    r1 = pk(rq[nt: nt + 8 * nb]); r2 = pk(yF[nt + 2: nt + 2 + 8 * nb]); r3 = pk(yA[nt + 2: nt + 2 + 8 * nb])
    frame = P.config_frame(p, S, clo, chi, S is None, sq, nt, ntot, 0, states, payload=True, play=play)
    return data, frame, (r1, r2, r3), cnt, ntot


def main():
    out, ok_all = [], True
    for (name, swv, runs) in SIMS:
        d = os.path.join(R.HERE, "build", "payload", name); os.makedirs(d, exist_ok=True)
        exp, groups, total = [], [([ord("I")], 8)], 8
        for run in runs:
            data, frame, dec, cnt, ntot = expected(run)
            total += 3 * len(data) + P.REPORT_LEN
            groups.append((list(frame) + list(data) + [0], total))
            exp.append((run, data, dec, cnt, ntot))
        with open(os.path.join(d, "cmds.txt"), "w") as f:
            for (bs, w) in groups:
                f.write(f"{len(bs)} {w} " + " ".join(str(x) for x in bs) + "\n")
        vvp = os.path.join(d, "sim.vvp"); dv = d.replace("\\", "/")
        r = subprocess.run(["iverilog", "-g2012", "-o", vvp, f'-Ptb_payload.DIR="{dv}"', f"-Ptb_payload.SW={swv}"] + SRC,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("COMPILE ERROR", r.stderr[:1500]); return 1
        r = subprocess.run(["vvp", vvp], capture_output=True, text=True)
        errs = [ln for ln in r.stdout.splitlines() if "ERROR" in ln]
        nhold = int(r.stdout.split("clocks with the output buffer full")[0].split(",")[-1]) if "output buffer full" in r.stdout else -1
        rx = bytes(int(x) for x in open(os.path.join(d, "rx.txt")).read().split())
        played = bytes(int(x) for x in open(os.path.join(d, "play.txt")).read().split())
        ok = not errs and nhold > 0
        try:
            ident = P.parse_ident(rx[:8]); ok &= ident["version"] == 2
            pos, want_play = 8, b""
            for (run, data, dec, cnt, ntot) in exp:
                n = len(data)
                got = P.split_words(rx[pos: pos + 3 * n]); pos += 3 * n
                rep = P.parse_report(rx[pos: pos + P.REPORT_LEN]); pos += P.REPORT_LEN
                same_dec = [g == e for g, e in zip(got, dec)]
                same_cnt = rep["counters"] == cnt and rep["sym_idx"] == ntot and rep["done"]
                ok &= all(same_dec) and same_cnt
                if run[8]:
                    want_play += {0x0000: dec[2], 0x0800: dec[0]}[swv]
                nerr = [sum(bin(a ^ b).count("1") for a, b in zip(e, data)) for e in dec]
                out.append(f"{name}: mu=2^-{run[0]} S={run[1]} {run[4]} dB, {n} bytes: decisions R1/R2/R3 identical to L2: "
                           f"{same_dec} | counters identical: {same_cnt} | bit errors R1/R2/R3 {nerr[0]}/{nerr[1]}/{nerr[2]}")
            same_play = played == want_play
            ok &= same_play
            out.append(f"{name}: played samples identical to the selected receiver's bytes: {same_play} ({len(played)} samples) | "
                       f"clocks with the output buffer full: {nhold}")
        except (ValueError, IndexError) as e:
            ok = False; out.append(f"{name}: decode error {e}; received {len(rx)} bytes")
        if errs: out.append(f"{name}: simulation errors: " + "; ".join(errs[:5]))
        ok_all &= ok
        print("\n".join(out[-(len(runs) + 1):]))
    out.append("ALL PASS" if ok_all else "SOME FAIL"); print(out[-1])
    with open(LOG, "w") as fh:
        fh.write("# payload transport through top_boolean vs L2, iverilog, level L3\n" + "\n".join(out) + "\n")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
