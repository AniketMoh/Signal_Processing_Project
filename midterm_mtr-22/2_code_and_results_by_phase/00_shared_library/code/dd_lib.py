# dd_lib.py -- R3 with the adaptation sources of PPR-22 Sec. 5.6 (level L1).  The LMS equations are the same as lms_lib.lms_receivers
# (y = w.u computed BEFORE the update, w <- w + mu*e*u); only the REFERENCE used in e changes:
#   training phase : known symbol d[n] (PRBS).  The switch to the payload mode is GATED: it happens at the first n >= n_min at which the
#                    running MSE (exponential average, time constant win symbols) is below gate_thr; if never, at n = N_T (forced, flagged).
#   payload phase  : decision-directed reference sign(y[n]); if pilot_period > 0, every pilot_period-th symbol after the switch is a
#                    known pilot and its true value is used instead (pilot-assisted mode).
# The transmitted sequence itself is not changed by the receiver mode (PRBS for n < N_T, payload after).
import numpy as np
from numba import njit


@njit(cache=True)
def r3_modes(r, d, L, mu, N_T, gate_thr, win, n_min, pilot_period):
    n_total = len(r)
    w = np.zeros(L); u = np.zeros(L)
    y = np.zeros(n_total); e_true = np.zeros(n_total); is_pilot = np.zeros(n_total, np.int8)
    m = 1.0; a = 1.0 / win
    training = True; n_sw = -1; forced = 0
    for n in range(n_total):
        for k in range(L - 1, 0, -1):
            u[k] = u[k - 1]
        u[0] = r[n]
        ya = 0.0
        for k in range(L):
            ya += w[k] * u[k]
        if training:
            ref = d[n]
            m = (1.0 - a) * m + a * (d[n] - ya) ** 2
            if n + 1 >= N_T:
                training = False; n_sw = n + 1; forced = 1
            elif n >= n_min and m < gate_thr:
                training = False; n_sw = n + 1
        else:
            if pilot_period > 0 and ((n - n_sw) % pilot_period) == 0:
                ref = d[n]; is_pilot[n] = 1
            else:
                ref = 1.0 if ya >= 0.0 else -1.0
        e = ref - ya
        y[n] = ya; e_true[n] = d[n] - ya
        for k in range(L):
            w[k] += mu * e * u[k]
    return y, e_true, n_sw, forced, is_pilot
