# rep6_tracking_theory.py -- Replication R6: LMS tracking trade-off, random-walk and deterministic-ramp variation.
# Sources and what was verified in them (see LITERATURE_NOTES / REPLICATION_REPORT):
#   * Random-walk model w_o(i) = w_o(i-1) + q(i), E||q||^2 = xi^2: steady-state error = xi^2/(2 mu) [drift/lag] + mu Tr(R) sigma_v^2 / 2 [gradient noise]
#     (arXiv 2004.01942, Eq. 17, converted from MSD to excess MSE for white input), optimum mu = xi/(sigma_v sqrt(Tr R)).
#   * Deterministic (non-zero-mean) drift: lag term xi^2/(mu^2 sigma^2) (arXiv 2004.01942, Eq. 19), optimum mu ~ xi^(2/3).
#   * Bershad & Macchi (DTIC ADA208618): chirp tracking, misadjustment = lag of order v^-2 + fluctuation of order v.
#   * Stationary excess MSE J_ex = J_min * (mu/2) Tr(R) (small mu) (IISc lecture notes, and Widrow et al.).
# System identification, N taps, white Gaussian input (variance 1), noise variance sv2.  Level L1 (float).
import sys, numpy as np
from numba import njit

N = 8; SV2 = 0.04

@njit(cache=True)
def track(mu, xi, kind, n_iter, skip, T_half, seed):
    """kind 0 = zero-mean random walk, 1 = deterministic ramp (triangle: direction reverses every T_half steps).
    Returns mean of sigma^2*||w_o - w||^2 (a priori, i.e. excess MSE) over the measured steps."""
    np.random.seed(seed)
    wo = np.zeros(N); w = np.zeros(N); u = np.zeros(N)
    tot = 0.0; cnt = 0
    sgn = 1.0
    for k in range(n_iter):
        # plant moves
        if kind == 0:
            for j in range(N):
                wo[j] += xi / np.sqrt(N) * np.random.randn()
        else:
            if k > 0 and k % T_half == 0:
                sgn = -sgn
            for j in range(N):
                wo[j] += sgn * xi / np.sqrt(N)
        # regressor, desired, update
        for j in range(N):
            u[j] = np.random.randn()
        y = 0.0; d = 0.0
        for j in range(N):
            y += w[j] * u[j]; d += wo[j] * u[j]
        d += np.sqrt(SV2) * np.random.randn()
        e = d - y
        # excess MSE bookkeeping (a priori, before the update)
        ok = False
        if kind == 0:
            ok = k >= skip
        else:
            ok = (k >= T_half) and ((k % T_half) >= skip)
        if ok:
            s = 0.0
            for j in range(N):
                s += (wo[j] - w[j]) ** 2
            tot += s; cnt += 1
        for j in range(N):
            w[j] += mu * e * u[j]
    return tot / cnt

def theory(mu, xi, kind):
    gn = mu * N * SV2 / 2.0                   # gradient-noise term  mu*Tr(R)*sv2/2
    lag = xi ** 2 / (2 * mu) if kind == 0 else xi ** 2 / mu ** 2
    return lag + gn, lag, gn

def refine_min(mus, vals):
    """parabola in log-log through the three points around the smallest value -> (mu_opt, min value)"""
    i = int(np.argmin(vals)); i = min(max(i, 1), len(mus) - 2)
    x = np.log(mus[i - 1:i + 2]); y = np.log(vals[i - 1:i + 2])
    a, b, c = np.polyfit(x, y, 2)
    xm = -b / (2 * a)
    return float(np.exp(xm)), float(np.exp(np.polyval([a, b, c], xm)))

if __name__ == '__main__':
    mus = np.geomspace(0.0004, 0.12, 15)
    xis = [0.0002, 0.0005, 0.001, 0.002, 0.004, 0.008]
    res = {}
    for kind in (0, 1):
        name = 'random walk' if kind == 0 else 'ramp'
        print(f"=== {name} ===", flush=True)
        mo_sim = []; mo_th = []
        for xi in xis:
            sim = []
            for mu in mus:
                T_half = int(max(20000, 40 / mu))
                n_iter = 2_000_000 if kind == 0 else 7 * T_half
                skip = int(10 / mu)
                sim.append(track(mu, xi, kind, n_iter, skip, T_half, 17 + kind))
            sim = np.array(sim)
            th = np.array([theory(m, xi, kind)[0] for m in mus])
            mu_s, _ = refine_min(mus, sim)
            mu_t = (xi / (np.sqrt(SV2) * np.sqrt(N))) if kind == 0 else (4 * xi ** 2 / (N * SV2)) ** (1 / 3)
            mo_sim.append(mu_s); mo_th.append(mu_t)
            j = int(np.argmin(sim))
            ratio_at_min = sim[j] / th[j]
            # local log-log slopes in the lag-dominated (first 3 points) and gradient-noise-dominated (last 3 points) parts
            s_lo = np.polyfit(np.log(mus[:3]), np.log(sim[:3]), 1)[0]
            s_hi = np.polyfit(np.log(mus[-3:]), np.log(sim[-3:]), 1)[0]
            print(f" xi={xi:.4f}: mu_opt sim {mu_s:.5f}  theory {mu_t:.5f}  (sim/theory {mu_s/mu_t:.3f}) | sim/theory EMSE at grid minimum {ratio_at_min:.3f}"
                  f" | slope at small mu {s_lo:+.2f} (theory {'-1' if kind==0 else '-2'}), at large mu {s_hi:+.2f} (theory +1)", flush=True)
            res[(kind, xi)] = (mus, sim, th)
        sl = np.polyfit(np.log(xis), np.log(mo_sim), 1)[0]
        slt = np.polyfit(np.log(xis), np.log(mo_th), 1)[0]
        print(f" exponent d log mu_opt / d log xi:  simulated {sl:.3f}   theory {slt:.3f}", flush=True)
    np.save('results/rep6_curves.npy', {str(k): v for k, v in res.items()}, allow_pickle=True)
