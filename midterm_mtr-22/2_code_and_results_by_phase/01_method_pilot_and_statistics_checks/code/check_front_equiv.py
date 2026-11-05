# check_front_equiv.py -- does the integer front end (fxp_front.py) change the L2 results compared with the earlier float front end?
# Same bits, same trajectory, same LFSR noise stream; only the way r is formed differs.  Receivers: fxp_receivers, B_acc 16 / B_mul 12, nearest, mu = 2^-8.
import numpy as np
from lms_lib import make_experiment, delayed_symbols, apply_channel
from fxp_lib import fxp_receivers, quantize_signal, LFSR_TAPS, _lfsr_noise
import fxp_front as ff

NT, NSYM, L = 6000, 60000, 16
print("seed S | r_q differs in (fraction of symbols) | max |r_q diff| | R3 MSE float-FE / int-FE | R3 errors float-FE / int-FE | R2 errors float / int")
for S in (20, 1000):
    for seed in (4001, 4002, 4003):
        ex = make_experiment(S, (40, 116), 14.0, seed, N_T=NT, N_eval=NSYM - NT)
        states = np.array(ff.lfsr_start_values(seed + 500000), np.int64)
        out = _lfsr_noise(NSYM, LFSR_TAPS, states.copy())                 # float stream = noise_int / 65536
        noise_int = np.round(out * 65536).astype(np.int64)
        sig = ex["sigma"]
        r_float = apply_channel(ex["x"], ex["taps"]) + sig * out
        rq_f = quantize_signal(r_float); dq = quantize_signal(delayed_symbols(ex["x"], 2))
        sq = ff.sigma_q_from_ebn0(14.0)
        rq_i, dq_i = ff.front_end_int(ex["bits"], ex["c"], noise_int, sq)
        assert np.array_equal(dq, dq_i)
        res = []
        for rq in (rq_f, rq_i):
            yA, yF, eA, eF, _, _, _ = fxp_receivers(rq, dq, L, 8, NT, 12, 16, 1, 10 ** 9)
            w = np.arange(NT, NSYM)
            mse = np.mean((eA[w] / 4096.0) ** 2)
            e3 = int(np.sum((yA[w] >= 0).astype(int) != ex["bits"][w - 2])); e2 = int(np.sum((yF[w] >= 0).astype(int) != ex["bits"][w - 2]))
            res.append((mse, e3, e2))
        dif = rq_f != rq_i
        print(f"{seed} {S:5d} | {dif.mean():.5f} | {np.abs(rq_f - rq_i).max()} | {res[0][0]:.6f} / {res[1][0]:.6f} | {res[0][1]} / {res[1][1]} | {res[0][2]} / {res[1][2]}")
