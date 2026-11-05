# l2_ref.py -- L2 (bit-true fixed point) reference for the complete chain, shared by the RTL tests and the board (L5) checks.
# Uses the mid-term L2 functions unchanged (lms_lib, fxp_front, fxp_lib); this file only assembles them.  The arithmetic is the
# one in 09_P7-P8_RTL/code/run_chain_tests.py; the only addition is the board payload, an LFSR x^31 + x^28 + 1 (payload_lfsr.v).
# Responsible member: Aniket Mohapatra (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
import csv, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PKG = os.path.join(REPO, "midterm_mtr-22", "2_code_and_results_by_phase")
MODEL = os.path.join(HERE, "build", "runnable_code")


def _build_model_copy():
    if os.path.isfile(os.path.join(MODEL, "fxp_lib.py")):
        return
    with open(os.path.join(PKG, "manifest.csv")) as fh:
        for row in csv.DictReader(fh):
            dst = os.path.join(MODEL, row["original_path_in_runnable_layout"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(PKG, row["location_in_this_package"]), dst)


_build_model_copy()
sys.path.insert(0, MODEL)
import numpy as np
from lms_lib import make_bits, lfsr_bits, triangle_counter
from fxp_lib import fxp_receivers
import fxp_front as ff
from config import CFG

L = 16
PAYLOAD_NBITS, PAYLOAD_TAPS = 31, (31, 28)


def payload_bits(n, seed):
    """Board payload: the same bits as payload_lfsr.v started from 'seed' (0 is replaced by 1, as in the RTL)."""
    return lfsr_bits(n, PAYLOAD_NBITS, PAYLOAD_TAPS, seed if seed else 1)


def chain(nsym, nt, b_acc, b_mul, rnd, p, S, c_lo, c_hi, sigma_q, noise_states, payload):
    """Run the L2 chain. S = None: static channel. payload: array of nsym - nt bits.
    Returns per-symbol (r_q, d_q, yA, yF, eA, eF) and the counters [n_eval, e1, e2, e3, sse2, sse3, stalls, updates]."""
    tr = lfsr_bits(nt, CFG["prbs_nbits"], CFG["prbs_taps"], CFG["prbs_seed"])
    bits = np.concatenate([tr, np.asarray(payload, dtype=np.int64)]).astype(np.int64)
    c = triangle_counter(nsym, nt, c_lo, c_hi, S)
    noise = ff.noise_int_stream(nsym, noise_states)
    rq, dq = ff.front_end_int(bits, c, noise, sigma_q)
    yA, yF, eA, eF, wH, stalls, updates = fxp_receivers(rq, dq, L, p, nt, b_mul, b_acc, rnd, 10 ** 9)
    w = np.arange(nt, nsym)
    cnt = [len(w),
           int(np.sum((rq[w] >= 0).astype(int) != bits[w])),
           int(np.sum((yF[w] >= 0).astype(int) != bits[w - 2])),
           int(np.sum((yA[w] >= 0).astype(int) != bits[w - 2])),
           int(np.sum(eF[w].astype(object) ** 2)), int(np.sum(eA[w].astype(object) ** 2)),
           int(stalls), int(updates)]
    return bits, np.stack([rq, dq, yA, yF, eA, eF], axis=1), cnt
