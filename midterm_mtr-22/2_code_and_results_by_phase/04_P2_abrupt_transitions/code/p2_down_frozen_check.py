"""Diagnostic (L1, final P2 configuration, 20 of the final seeds): why is R2's measured MSE after the 'down' step (c 116 -> 40)
1-3 % BELOW the analytic frozen-filter value 1 - 2 w_A.p_B + w_A.R_B.w_A?  Compare, per seed, the measured R2 MSE with the analytic MSE of the
ACTUAL frozen weights (same formula, w = the weights R2 really froze).  If they agree, the difference is in the weights, not in the measurement."""
import sys; sys.path.insert(0, ".")
import numpy as np
from exp_lib import *
EB = 16.0; S2 = sigma_from_ebn0(EB) ** 2; N_T, N_PRE, N_POST = 60000, 20000, 100000; N_C = N_T + N_PRE
wA, JA, RA, pA = Rp_const(116, S2); wB, JB, RB, pB = Rp_const(40, S2)
J_w = lambda w: 1 - 2 * w @ pB + w @ RB @ w
print(f"analytic MSE of the Wiener filter w_A on channel B: {J_w(wA):.4f}")
c = step_counter(116, 40, N_T, N_PRE, N_POST)
for p in (7, 10):
    meas, ana, dist = [], [], []
    for sd in range(2000, 2020):
        ex = make_exp_from_counter(c, N_T, EB, sd); yA, yF, eA, eF, wH = run_lms(ex, 2.0 ** -p, 1)
        wf = wH[N_T - 1]                                   # weights after the update at n = N_T-1 = the frozen copy
        meas.append(np.mean(eF[N_C + L:] ** 2)); ana.append(J_w(wf)); dist.append(np.linalg.norm(wf - wA) / np.linalg.norm(wA))
    print(f"mu=2^-{p}: measured R2 MSE {np.mean(meas):.4f}   analytic MSE of the ACTUAL frozen weights {np.mean(ana):.4f}   "
          f"(difference {100*(np.mean(meas)/np.mean(ana)-1):+.2f} %);  relative distance |w_frozen - w_A|/|w_A| = {np.mean(dist):.4f};  "
          f"spread of analytic values across seeds {np.std(ana):.4f}")

# hypothesis test: every seed uses the SAME PRBS training segment, so its finite-sample correlation offsets the frozen weights identically in all
# seeds.  Diagnostic only (the frozen protocol keeps the PRBS): replace the training bits by seed-dependent random bits.
print("diagnostic with seed-dependent RANDOM training bits (not the frozen protocol):")
for p in (7, 10):
    meas, ana = [], []
    for sd in range(2000, 2020):
        bits = make_bits(len(c), sd + 777000).astype(np.int64); x = 2.0 * bits - 1
        taps = taps_from_counter(c, H2); r = apply_channel(x, taps) + make_noise(len(c), np.sqrt(S2), sd + 500000)
        ex = dict(bits=bits, x=x, c=c, taps=taps, r=r, sigma=np.sqrt(S2), N_T=N_T, n_total=len(c))
        yA, yF, eA, eF, wH = run_lms(ex, 2.0 ** -p, 1); meas.append(np.mean(eF[N_C + L:] ** 2)); ana.append(J_w(wH[N_T - 1]))
    print(f"mu=2^-{p}: measured R2 MSE {np.mean(meas):.4f} (analytic w_A value 0.8049; mean relative difference {100*(np.mean(meas)/J_w(wA)-1):+.2f} %, seed spread {np.std(meas):.4f})")

# mean-weight model: after N_T training symbols from zero weights, E[w] = w_A - (I - mu R_A)^N_T w_A  (slowest mode not fully converged)
lamA, QA = np.linalg.eigh(RA)
for p in (7, 8, 9, 10):
    mu = 2.0 ** -p
    for NT_ in (30000, 60000, 120000):
        Ew = wA - QA @ (((1 - mu * lamA) ** NT_) * (QA.T @ wA))
        print(f"model mu=2^-{p:2d} N_T={NT_:6d}: J_B(E[w]) = {J_w(Ew):.4f}  ({100*(J_w(Ew)/J_w(wA)-1):+.2f} % vs w_A);  |E[w]-w_A|/|w_A| = {np.linalg.norm(Ew-wA)/np.linalg.norm(wA):.4f}")
