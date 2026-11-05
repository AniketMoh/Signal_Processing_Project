# c5c_dd_mu.py -- DD divergence vs step size and SNR at S = 28 (primary channel, Delta = 2, gate thr 0.1, 20 seeds).  Level L1.
# Divergence is judged by the ratio BER_DD / BER_supervised on identical data (the window criterion of c5_dd.py is not usable when the
# supervised BER itself is near 0.1).
import numpy as np, json
from config import CFG
from lms_lib import triangle_counter, delayed_symbols, lms_receivers
from exp_lib import make_exp_from_counter
from dd_lib import r3_modes
from sweep import n_eval_for
from c5_dd import ber_mse
L = CFG["L"]; NT = 30000; OUT = "results/commit"; log = open(f"{OUT}/c5c_log.txt", "w")
def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()
res = {}
for S in (28, 1000):
    ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
    for p in (5, 6, 7, 8):
        for snr in (4.0, 6.0, 8.0, 10.0, 12.0, 14.0):
            ed = nd = es = ns = 0; per_seed_bad = 0
            for sd in range(2000, 2020):
                ex = make_exp_from_counter(c, NT, snr, sd); d = delayed_symbols(ex["x"], 2)
                y, e, k, fo, _ = r3_modes(ex["r"], d, L, 2.0 ** -p, NT, 0.1, 1000.0, 2000, 0)
                a, b, _ = ber_mse(y, e, ex["bits"], NT, len(c)); ed += a; nd += b
                yA, yF, eA, eF, _ = lms_receivers(ex["r"], d, L, 2.0 ** -p, NT, 0, 10 ** 9)
                a2, b2, _ = ber_mse(yA, eA, ex["bits"], NT, len(c)); es += a2; ns += b2
                per_seed_bad += (a > 2 * a2 + 20)
            res[f"{S}|{p}|{snr}"] = dict(ber_dd=ed / nd, ber_sup=es / ns, bad_seeds=int(per_seed_bad))
            lg(f"S={S:5d} mu=2^-{p} {snr:4.0f} dB: BER DD {ed/nd:.3e}  supervised {es/ns:.3e}  ratio {ed/max(es,1):.2f}  seeds with DD errors > 2x supervised + 20: {per_seed_bad}/20")
json.dump(res, open(f"{OUT}/c5c.json", "w"))
