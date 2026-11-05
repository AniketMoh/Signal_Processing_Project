# c5_dd.py -- PPR-22 Sec. 5.6 and Table 5: decision-directed (DD) and pilot-assisted adaptation of R3, compared with supervised evaluation
# on identical data, channel and noise.  Level L1, primary channel 40-116, Delta = 2, N_T = 30000 (maximum training length).
#  Part 1: gate threshold (running MSE, time constant 1000 symbols, n_min = 2000): switch time and the static-channel result.
#  Part 2: tracking with DD vs supervised vs pilot-assisted, BER and MSE vs S, 14 dB, mu = 2^-6, 2^-8, 2^-10, 20 seeds.
#  Part 3: divergence (loss of lock) of DD: a run has LOST LOCK if any 2000-symbol window after the switch has BER > 0.1;
#          the divergence threshold is reported as the slowest S at which at least half of the seeds lose lock (and the SNR sweep at fixed S).
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from config import CFG, sigma_from_ebn0
from lms_lib import triangle_counter, delayed_symbols, lms_receivers
from exp_lib import make_exp_from_counter
from dd_lib import r3_modes
from sweep import n_eval_for
L = CFG["L"]; NT = 30000; OUT = "results/commit"
log = None
def lg(s):
    print(s, flush=True); log.write(s + "\n"); log.flush()
WIN, NMIN = 1000.0, 2000

def lock_lost(y, bits, n0, n1, wlen=2000):
    ref = np.zeros(len(bits), np.int64); ref[2:] = bits[:-2]
    err = ((y[n0:n1] >= 0).astype(int) != ref[n0:n1]).astype(float)
    if len(err) < wlen: return False, float(err.mean())
    cs = np.concatenate([[0], np.cumsum(err)]); wb = (cs[wlen:] - cs[:-wlen]) / wlen
    return bool(wb.max() > 0.1), float(err.mean())

def ber_mse(y, e, bits, n0, n1, mask=None):
    ref = np.zeros(len(bits), np.int64); ref[2:] = bits[:-2]
    sel = np.arange(n0, n1) if mask is None else np.arange(n0, n1)[mask[n0:n1] == 0]
    return int(np.sum((y[sel] >= 0).astype(int) != ref[sel])), len(sel), float(np.mean(e[n0:n1] ** 2))

if __name__ == '__main__':
    log = open(f"{OUT}/c5_log.txt", "a")
    lg('(rerun guard added 24 Oct; results identical, deterministic seeds)')
    res = {}
    # ---------- Part 1: gate threshold
    lg("Part 1: gated switch, static primary channel c = 40 and c = 116, 14 dB, mu = 2^-8, 10 seeds.  thr = running-MSE threshold")
    for c0 in (40, 116):
        c = np.full(NT + 100000, c0)
        for thr in (0.05, 0.1, 0.2, 0.4, 0.8):
            sw, fo, lost, bers = [], 0, 0, []
            for sd in range(2100, 2110):
                ex = make_exp_from_counter(c, NT, 14.0, sd); d = delayed_symbols(ex["x"], 2)
                y, e, nsw, forced, _ = r3_modes(ex["r"], d, L, 2.0 ** -8, NT, thr, WIN, NMIN, 0)
                l, b = lock_lost(y, ex["bits"], NT, len(c)); sw.append(nsw); fo += forced; lost += l; bers.append(b)
            res[f"gate|{c0}|{thr}"] = dict(switch_median=float(np.median(sw)), forced=fo, lost=lost, ber=float(np.mean(bers)))
            lg(f"  c={c0:3d} thr={thr:4.2f}: switch at symbol median {np.median(sw):7.0f} (min {min(sw)}, max {max(sw)}), forced at N_T in {fo}/10, lost lock {lost}/10, payload BER {np.mean(bers):.2e}")

    # ---------- Part 2 and 3: tracking
    THR = 0.1
    lg(f"Part 2: tracking, 14 dB, gate thr = {THR}, 20 seeds (2000-2019).  modes: SUP supervised (reference = true symbol), DD, PIL10/PIL50 pilot every 10/50 symbols (BER on non-pilot symbols)")
    Sg = [1000, 320, 112, 56, 28, 14, 5, 2, 1]
    for p in (6, 8, 10):
        mu = 2.0 ** -p
        for S in Sg:
            ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
            acc = {k: [0, 0, [], 0] for k in ("SUP", "DD", "PIL10", "PIL50")}
            for sd in range(2000, 2020):
                ex = make_exp_from_counter(c, NT, 14.0, sd); d = delayed_symbols(ex["x"], 2)
                yA, yF, eA, eF, _ = lms_receivers(ex["r"], d, L, mu, NT, 0, 10 ** 9)
                er, n, ms = ber_mse(yA, eA, ex["bits"], NT, len(c)); a = acc["SUP"]; a[0] += er; a[1] += n; a[2].append(ms)
                for key, pp in (("DD", 0), ("PIL10", 10), ("PIL50", 50)):
                    y, e, nsw, forced, pil = r3_modes(ex["r"], d, L, mu, NT, THR, WIN, NMIN, pp)
                    er, n, ms = ber_mse(y, e, ex["bits"], NT, len(c), pil)
                    l, _ = lock_lost(y, ex["bits"], NT, len(c))
                    a = acc[key]; a[0] += er; a[1] += n; a[2].append(ms); a[3] += l
            row = {k: dict(ber=v[0] / v[1], err=v[0], mse=float(np.mean(v[2])), lost=v[3]) for k, v in acc.items()}
            res[f"track|{p}|{S}"] = row
            lg(f"  mu=2^-{p:2d} S={S:5d}: BER SUP {row['SUP']['ber']:.2e} | DD {row['DD']['ber']:.2e} (lost {row['DD']['lost']}/20) | PIL50 {row['PIL50']['ber']:.2e} (lost {row['PIL50']['lost']}/20) | PIL10 {row['PIL10']['ber']:.2e} (lost {row['PIL10']['lost']}/20)"
               f"   MSE SUP/DD/PIL10 {row['SUP']['mse']:.4f}/{row['DD']['mse']:.4f}/{row['PIL10']['mse']:.4f}")

    lg("Part 3: DD loss of lock vs SNR at fixed rate, mu = 2^-8, S = 28 and S = 1000, 20 seeds")
    for S in (1000, 28):
        ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
        for snr in (6.0, 8.0, 10.0, 12.0, 14.0):
            lost = 0; errs = 0; nn = 0; lostS = 0
            for sd in range(2000, 2020):
                ex = make_exp_from_counter(c, NT, snr, sd); d = delayed_symbols(ex["x"], 2)
                y, e, nsw, forced, _ = r3_modes(ex["r"], d, L, 2.0 ** -8, NT, THR, WIN, NMIN, 0)
                l, b = lock_lost(y, ex["bits"], NT, len(c)); lost += l
                yA, yF, eA, eF, _ = lms_receivers(ex["r"], d, L, 2.0 ** -8, NT, 0, 10 ** 9)
                ls, bs = lock_lost(yA, ex["bits"], NT, len(c)); lostS += ls
                errs += b; nn += 1
            res[f"snr|{S}|{snr}"] = dict(dd_lost=lost, sup_lost=lostS, dd_ber=errs / nn)
            lg(f"  S={S:5d} {snr:4.1f} dB: DD lost lock {lost}/20 (mean BER {errs/nn:.2e}); supervised runs with a >10 % 2000-symbol window: {lostS}/20")
    json.dump(res, open(f"{OUT}/c5.json", "w"))
