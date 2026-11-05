# c5b_dd_stress.py -- where does decision-directed (DD) adaptation lose lock?  (c5_dd.py found no loss of lock at 6-14 dB on the primary channel.)
# Level L1, primary channel, Delta = 2, same lock criterion as c5_dd.py (any 2000-symbol window after the switch with BER > 0.1).
#  (a) low SNR: 0, 2, 4, 6 dB;  (b) too little training: switch forced after n_sw symbols (gate disabled);  (c) abrupt jumps 40 <-> 116.
import numpy as np, json
from config import CFG
from lms_lib import triangle_counter, delayed_symbols, lms_receivers
from exp_lib import make_exp_from_counter, step_counter
from dd_lib import r3_modes
from sweep import n_eval_for
from c5_dd import lock_lost, ber_mse
L = CFG["L"]; NT = 30000; OUT = "results/commit"; log = open(f"{OUT}/c5b_log.txt", "w")
def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()
res = {}
lg("(a) low SNR, gate thr 0.1 (forced at N_T if never reached), 20 seeds; entries: DD lost lock / runs, DD BER, supervised BER")
for p in (6, 8):
    for S in (1000, 28, 5):
        ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
        for snr in (0.0, 2.0, 4.0, 6.0):
            lost = 0; e_dd = n_dd = e_s = n_s = 0; forced = 0
            for sd in range(2000, 2020):
                ex = make_exp_from_counter(c, NT, snr, sd); d = delayed_symbols(ex["x"], 2)
                y, e, nsw, fo, _ = r3_modes(ex["r"], d, L, 2.0 ** -p, NT, 0.1, 1000.0, 2000, 0)
                l, _ = lock_lost(y, ex["bits"], NT, len(c)); lost += l; forced += fo
                a, b, _ = ber_mse(y, e, ex["bits"], NT, len(c)); e_dd += a; n_dd += b
                yA, yF, eA, eF, _ = lms_receivers(ex["r"], d, L, 2.0 ** -p, NT, 0, 10 ** 9)
                a, b, _ = ber_mse(yA, eA, ex["bits"], NT, len(c)); e_s += a; n_s += b
            res[f"snr|{p}|{S}|{snr}"] = dict(lost=lost, forced=forced, ber_dd=e_dd / n_dd, ber_sup=e_s / n_s)
            lg(f"  mu=2^-{p} S={S:5d} {snr:3.0f} dB: DD lost {lost}/20 (gate forced at N_T in {forced}/20), BER DD {e_dd/n_dd:.3e}, supervised {e_s/n_s:.3e}")

lg("(b) too little training: DD switch forced after n_sw symbols (no gate), mu = 2^-8, 20 seeds, 14 dB")
for name, c in (("static c=116", np.full(NT + 100000, 116)), ("static c=40", np.full(NT + 100000, 40)),
                ("triangle S=28", triangle_counter(NT + n_eval_for(28, 40, 116), NT, 40, 116, 28))):
    for nsw in (25, 50, 100, 200, 400, 800, 1600):
        lost = 0
        for sd in range(2000, 2020):
            ex = make_exp_from_counter(c, NT, 14.0, sd); d = delayed_symbols(ex["x"], 2)
            y, e, k, fo, _ = r3_modes(ex["r"], d, L, 2.0 ** -8, NT, 1e9, 1000.0, nsw - 1, 0)
            l, _ = lock_lost(y, ex["bits"], nsw, len(c)); lost += l
        res[f"short|{name}|{nsw}"] = lost
        lg(f"  {name:14s} switch after {nsw:5d} training symbols: DD lost lock {lost}/20")

lg("(c) abrupt jump (P2-type), channel static at cA during training, jump to cB 20000 symbols after the switch point, DD with gate thr 0.1, mu = 2^-8, 20 seeds")
for snr in (14.0, 10.0, 6.0):
    for cA, cB in ((40, 116), (116, 40), (40, 77)):
        c = step_counter(cA, cB, NT, 20000, 60000)
        lost = 0; lost_s = 0
        for sd in range(2000, 2020):
            ex = make_exp_from_counter(c, NT, snr, sd); d = delayed_symbols(ex["x"], 2)
            y, e, k, fo, _ = r3_modes(ex["r"], d, L, 2.0 ** -8, NT, 0.1, 1000.0, 2000, 0)
            l, _ = lock_lost(y, ex["bits"], NT, len(c)); lost += l
            yA, yF, eA, eF, _ = lms_receivers(ex["r"], d, L, 2.0 ** -8, NT, 0, 10 ** 9)
            l2, _ = lock_lost(yA, ex["bits"], NT, len(c)); lost_s += l2
        res[f"jump|{snr}|{cA}|{cB}"] = dict(dd=lost, sup=lost_s)
        lg(f"  {snr:4.0f} dB jump {cA}->{cB}: DD lost lock {lost}/20, supervised flagged {lost_s}/20")
json.dump(res, open(f"{OUT}/c5b.json", "w"))
