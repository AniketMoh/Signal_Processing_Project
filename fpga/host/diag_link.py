# diag_link.py -- PC -> board link test for payload mode (level L5 diagnostics).
# Runs repeated payload transfers and reads the board's link counters ('D') before and after each one, so a lost byte can be
# located: never received by the UART, received with a framing error, or received but not accepted as payload.
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
# Usage: python diag_link.py [--trials 20] [--bytes 3000] [--gap-ms 0]
import argparse, os, struct, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
import numpy as np
import protocol as P
import run_payload as RP
from run_board import Board, find_port


def diag(b):
    b.s.reset_input_buffer(); b.s.write(b"D")
    r = b.read_exact(19, 2.0)
    if r[:3] != b"DBG":
        raise ValueError("bad diagnostics reply %r" % r[:8])
    return struct.unpack("<IIII", r[3:])           # bytes received, framing errors, payload accepted, payload dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--bytes", type=int, default=3000)
    ap.add_argument("--gap-ms", type=float, default=0.0, help="pause between the 'X' frame and the first payload byte")
    a = ap.parse_args()
    b = Board(find_port()); print("board:", b.ident())
    lost_runs = 0
    for t in range(a.trials):
        data = np.random.default_rng(100 + t).integers(0, 256, a.bytes, dtype=np.uint8).tobytes()
        frame = RP.frame_for(len(data), 8, None, 16.0, 700001)
        d0 = diag(b)
        s = b.s; s.reset_input_buffer(); s.write(frame); s.flush()
        if a.gap_ms: time.sleep(a.gap_ms / 1000)
        buf = data + b"\x00"; sent = 0; out = bytearray(); last = time.time()
        while time.time() - last < 1.5:
            k = min(len(out) // 3 + RP.WINDOW - sent, len(buf) - sent, 256)
            if k > 0: s.write(buf[sent:sent + k]); sent += k
            c = s.read(max(1, s.in_waiting))
            if c: out += c; last = time.time()
        d1 = diag(b)
        n = (len(out) - P.REPORT_LEN) // 3
        dr, df, dp, dd = (d1[i] - d0[i] for i in range(4))
        ok = n == len(data)
        lost_runs += not ok
        print(f"trial {t:2d}: {'complete' if ok else 'SHORT by %d' % (len(data) - n):12s} | UART bytes {dr} of {len(frame) + len(buf)} sent "
              f"| framing errors {df} | payload accepted {dp} of {len(buf)} | dropped (buffer full) {dd}")
    print(f"{lost_runs} of {a.trials} runs short")


if __name__ == "__main__":
    main()
