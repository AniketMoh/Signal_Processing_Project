# run_board.py -- L5 measurements on the Boolean Board through the host_if.v protocol (USB-UART, 115200 baud).
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
#   python run_board.py verify     board counters vs the L2 model, count for count, for a set of configurations
#   python run_board.py sweep      BER of R1/R2/R3 and MSE of R2/R3 against the variation rate S (board only, long runs)
#   python run_board.py ident      identification of the loaded bitstream
# Options: --port COM8 (default: the first FTDI port)
# Every output line and file is labelled with its level: L5 = measured on the board, L2 = bit-true model.
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
import serial
from serial.tools import list_ports
import protocol as P

RESULTS = os.path.join(HERE, "results")
SYM_RATE = 100e6 / 16                      # symbols per second on the board (one symbol per 16 clocks at 100 MHz)


def find_port():
    for p in list_ports.comports():
        if (p.manufacturer or "").upper().startswith("FTDI") or "USB Serial" in (p.description or ""):
            return p.device
    raise SystemExit("no FTDI serial port found; give --port")


class Board:
    def __init__(self, port):
        self.port = port
        self.open()

    def open(self):
        self.s = serial.Serial(self.port, 115200, timeout=0.5)
        time.sleep(0.1)
        self.s.reset_input_buffer()

    def reopen(self):
        try:
            self.s.close()
        except serial.SerialException:
            pass
        time.sleep(2.0)
        self.open()

    def read_exact(self, n, timeout):
        buf, t0 = bytearray(), time.time()
        while len(buf) < n and time.time() - t0 < timeout:
            buf += self.s.read(n - len(buf))
        if len(buf) != n:
            raise TimeoutError(f"expected {n} bytes, got {len(buf)}")
        return bytes(buf)

    def ident(self):
        self.s.reset_input_buffer(); self.s.write(b"I")
        return P.parse_ident(self.read_exact(8, 2.0))

    def run(self, p, S, c_lo, c_hi, sigma_q, n_t, n_total, pay_seed, seeds, tries=3):
        # Every 'X' reloads all seeds and restarts from w = 0, so repeating a run after a USB-serial dropout gives the same
        # counters; the repeat is logged.
        frame = P.config_frame(p, S, c_lo, c_hi, S is None, sigma_q, n_t, n_total, pay_seed, seeds)
        for k in range(tries):
            try:
                self.s.reset_input_buffer()
                self.s.write(frame)
                t0 = time.time()
                rep = P.parse_report(self.read_exact(P.REPORT_LEN, n_total / SYM_RATE + 5.0))
                return rep, time.time() - t0
            except (serial.SerialException, TimeoutError, ValueError) as e:
                print(f"  serial problem ({e}); reopening the port and repeating the run ({k + 1}/{tries})")
                if k == tries - 1:
                    raise
                self.reopen()


def cmd_ident(b):
    print("identification:", b.ident())


# p, S (None = static), c_lo, c_hi, ebn0, noise seed, payload seed, N_T, N_total
VERIFY = [
    (8,  28,   40, 116, 10.0, 2000, 12345, 30000, 400000),     # demo operating point, near S* for mu = 2^-8
    (8,  1000, 40, 116, 10.0, 2001, 1,     30000, 400000),     # slow variation
    (8,  5,    40, 116, 10.0, 2002, 99,    30000, 400000),     # fast variation (R3 loses tracking)
    (5,  1,    40, 116, 8.0,  2003, 7,     30000, 300000),     # largest mu, fastest channel
    (11, 224,  40, 116, 12.0, 2004, 5,     30000, 300000),     # smallest FPGA mu
    (8,  None, 40, 116, 10.0, 2005, 3,     30000, 300000),     # static channel
    (8,  50,   26, 77,  14.0, 2006, 11,    30000, 300000),     # control channel
    (6,  112,  40, 116, 6.0,  2007, 123,   30000, 1000000),    # long run, low SNR
]


def cmd_verify(b, ident):
    import l2_ref as R
    os.makedirs(RESULTS, exist_ok=True)
    rows, ok_all = [], True
    for (p, S, clo, chi, eb, ns, ps, nt, ntot) in VERIFY:
        states = R.ff.lfsr_start_values(ns + 500000)
        sq = R.ff.sigma_q_from_ebn0(eb)
        rep, dt = b.run(p, S, clo, chi, sq, nt, ntot, ps, states)
        t0 = time.time()
        _, _, l2 = R.chain(ntot, nt, ident["B_ACC"], ident["B_MUL"], ident["RND"], p, S, clo, chi, sq, states,
                           R.payload_bits(ntot - nt, ps))
        same = rep["counters"] == l2 and rep["sym_idx"] == ntot and rep["done"]
        ok_all &= same
        row = dict(p=p, S=S, c_lo=clo, c_hi=chi, ebn0=eb, noise_seed=ns, payload_seed=ps, n_t=nt, n_total=ntot,
                   board_L5=rep["counters"], model_L2=l2, identical=same, board_seconds=round(dt, 2),
                   model_seconds=round(time.time() - t0, 1))
        rows.append(row)
        print(f"mu=2^-{p:<2} S={str(S):>5} c={clo}..{chi} {eb:4.1f} dB n={ntot:>8}: board (L5) == model (L2): {same} "
              f"| err R1/R2/R3 = {rep['counters'][1]}/{rep['counters'][2]}/{rep['counters'][3]} of {rep['counters'][0]}")
    print("ALL IDENTICAL" if ok_all else "SOME DIFFER")
    out = dict(level="L5 board counters vs L2 bit-true model", build=ident, rows=rows, all_identical=ok_all,
               date=time.strftime("%Y-%m-%d %H:%M"))
    name = "board_verify_m%d_a%d_r%d.json" % (ident["B_MUL"], ident["B_ACC"], ident["RND"])
    with open(os.path.join(RESULTS, name), "w") as fh:
        json.dump(out, fh, indent=1)
    return 0 if ok_all else 1


def cmd_sweep(b, ident, ebn0, p, n_eval):
    import l2_ref as R
    os.makedirs(RESULTS, exist_ok=True)
    states = R.ff.lfsr_start_values(2000 + 500000)
    sq = R.ff.sigma_q_from_ebn0(ebn0)
    nt = 30000
    rows = []
    grid = [None, 5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1]
    for S in grid:
        # whole triangle periods (152*S symbols) as in the L1 window rule, at least n_eval symbols
        per = 152 * S if S else 1
        ne = max(1, round(n_eval / per)) * per if S else n_eval
        rep, dt = b.run(p, S, 40, 116, sq, nt, nt + ne, 777, states)
        n, e1, e2, e3, s2, s3, st, up = rep["counters"]
        row = dict(S=S, n_eval=n, err=[e1, e2, e3], ber=[e1 / n, e2 / n, e3 / n],
                   mse=[s2 / n / 2 ** 24, s3 / n / 2 ** 24], stall_fraction=st / up if up else None, seconds=round(dt, 1))
        rows.append(row)
        print(f"S={str(S):>5} n={n:>9}  BER R1 {e1/n:.3e}  R2 {e2/n:.3e}  R3 {e3/n:.3e}  MSE R2 {row['mse'][0]:.4f}  R3 {row['mse'][1]:.4f}")
    out = dict(level="L5 (measured on the Boolean Board, LFSR sum-of-uniforms noise; BER quoted only down to about 1e-4)",
               build=ident, ebn0_db=ebn0, mu=f"2^-{p}", channel="primary c 40..116", n_t=nt, noise_seed=2000,
               payload_seed=777, rows=rows, date=time.strftime("%Y-%m-%d %H:%M"))
    name = f"board_sweep_m{ident['B_MUL']}_a{ident['B_ACC']}_r{ident['RND']}_{ebn0:g}dB_mu2-{p}.json"
    with open(os.path.join(RESULTS, name), "w") as fh:
        json.dump(out, fh, indent=1)
    print("written", name)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ident", "verify", "sweep"])
    ap.add_argument("--port")
    ap.add_argument("--ebn0", type=float, default=10.0)
    ap.add_argument("--p", type=int, default=8)
    ap.add_argument("--n-eval", type=int, default=20_000_000)
    a = ap.parse_args()
    b = Board(a.port or find_port())
    ident = b.ident()
    print("board:", ident)
    if a.cmd == "ident":
        return 0
    if a.cmd == "verify":
        return cmd_verify(b, ident)
    return cmd_sweep(b, ident, a.ebn0, a.p, a.n_eval)


if __name__ == "__main__":
    sys.exit(main())
