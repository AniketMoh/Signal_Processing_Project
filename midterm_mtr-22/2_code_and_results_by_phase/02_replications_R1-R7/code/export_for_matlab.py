# export_for_matlab.py -- data for the MathWorks behavioural cross-check of the Python LMS model (PPR-22 Sec. 12.6).
# Static primary channel c = 40 and c = 116, 14 dB, 60000 symbols, PRBS training for all symbols (supervised), mu = 2^-8, L = 16, Delta = 2.
# Writes matlab/xcheck_c<c>.csv with columns: r, d (= x[n-2]), and matlab/xcheck_python_results.txt with the Python model's numbers.
import numpy as np
from config import sigma_from_ebn0
from lms_lib import delayed_symbols, lms_receivers
from exp_lib import make_exp_from_counter
out = open("matlab/xcheck_python_results.txt", "w")
for c0 in (40, 116):
    c = np.full(60000, c0)
    ex = make_exp_from_counter(c, 60000, 14.0, 8100 + c0)          # N_T = whole length: supervised throughout
    d = delayed_symbols(ex["x"], 2)
    np.savetxt(f"matlab/xcheck_c{c0}.csv", np.stack([ex["r"], d], 1), delimiter=",", fmt="%.10f")
    yA, yF, eA, eF, wH = lms_receivers(ex["r"], d, 16, 2.0 ** -8, 60005, 0, 100)
    mse = np.mean(eA[30000:] ** 2)
    out.write(f"c={c0}: Python LMS MSE (symbols 30000-59999) = {mse:.6f}; weights at symbol 59900 = " + " ".join(f"{w:.5f}" for w in wH[-1]) + "\n")
    print(f"c={c0}: MSE {mse:.6f}")
