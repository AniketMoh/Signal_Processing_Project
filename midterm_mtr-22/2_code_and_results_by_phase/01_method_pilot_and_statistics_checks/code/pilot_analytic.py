# pilot_analytic.py -- L1 ANALYTIC pilot (no LMS run, no random data).
# Question: for each candidate channel and Eb/N0, how much "room" is there to measure tracking loss?
# Uses the quasi-static oracle (channel treated as constant inside the equalizer window), which is accurate for slow ramps.
import json
import numpy as np
from config import CFG, DA, sigma_from_ebn0
from lms_lib import taps_from_counter, r1_exact_ber

L, M = CFG["L"], CFG["M"]


def stats_const(a, Delta, sigma2):
    """R and p for a constant channel [1, a, h2]."""
    h = np.array([1.0, a, CFG["h2"]])
    H = np.zeros((L, L + M - 1))
    for j in range(L):
        for k in range(M):
            H[j, j + k] = h[k]
    return H @ H.T + sigma2 * np.eye(L), H[:, Delta].copy()


def analyse(c_lo, c_hi, ebn0):
    sig2 = sigma_from_ebn0(ebn0) ** 2
    cs = np.arange(c_lo, c_hi + 1)
    a = cs * DA
    wgt = np.ones(len(cs)); wgt[0] = wgt[-1] = 0.5; wgt /= wgt.sum()   # triangle visits the ends half as often
    # choose one fixed Delta: minimise the trajectory-averaged oracle MSE
    meanJ = []
    for D in range(L + M - 1):
        J = []
        for ai in a:
            R, p = stats_const(ai, D, sig2)
            J.append(1 - p @ np.linalg.solve(R, p))
        meanJ.append(float(np.dot(wgt, J)))
    Dfix = int(np.argmin(meanJ))
    # per-a best Delta (only to measure the penalty of using one Delta)
    bestJ = []
    for ai in a:
        Js = []
        for D in range(L + M - 1):
            R, p = stats_const(ai, D, sig2)
            Js.append(1 - p @ np.linalg.solve(R, p))
        bestJ.append(min(Js))
    Jor, conds, Rs, ps = [], [], 0, 0
    for i, ai in enumerate(a):
        R, p = stats_const(ai, Dfix, sig2)
        Jor.append(1 - p @ np.linalg.solve(R, p))
        ev = np.linalg.eigvalsh(R); conds.append(ev[-1] / ev[0])
        Rs = Rs + wgt[i] * R; ps = ps + wgt[i] * p
    Jor = np.array(Jor)
    wbar = np.linalg.solve(Rs, ps)                       # best single fixed filter for the average channel
    w0 = np.linalg.solve(*stats_const(a[0], Dfix, sig2))  # filter trained at a_lo (what R2 holds)
    def J_of(w):
        out = []
        for ai in a:
            R, p = stats_const(ai, Dfix, sig2)
            out.append(1 - 2 * w @ p + w @ R @ w)
        return float(np.dot(wgt, out))
    J_or_mean = float(np.dot(wgt, Jor))
    w_grid = np.linspace(0, np.pi, 2001)
    minH = min(abs(1 + ai * np.exp(-1j * w_grid) + CFG["h2"] * np.exp(-2j * w_grid)).min() for ai in a)
    return dict(c_lo=c_lo, c_hi=c_hi, a_lo=float(a[0]), a_hi=float(a[-1]), ebn0=ebn0, Delta=Dfix,
                J_or_mean=J_or_mean,
                delta_penalty=float(np.dot(wgt, Jor) / np.dot(wgt, bestJ) - 1),
                eps_plateau=J_of(wbar) / J_or_mean - 1,
                eps_frozen_lo=J_of(w0) / J_or_mean - 1,
                cond_max=float(max(conds)), min_abs_H=float(minH),
                r1_ber_lo=r1_exact_ber(a[0], CFG["h2"], np.sqrt(sig2)),
                r1_ber_hi=r1_exact_ber(a[-1], CFG["h2"], np.sqrt(sig2)),
                tr_R=float(np.trace(stats_const(a[-1], Dfix, sig2)[0])))


if __name__ == "__main__":
    cands = {"mild": CFG["mild"], "A (0.50-0.90)": (64, 115), "primary (0.31-0.91)": CFG["primary"]}
    res = []
    print(f"L={L}  (analytic, quasi-static oracle)")
    print(f"{'channel':22s} {'Eb/N0':>5s} {'D':>2s} {'J_or':>7s} {'eps_plat':>8s} {'eps_froz':>8s} {'condR':>6s} {'min|H|':>6s} {'R1 lo':>9s} {'R1 hi':>9s} {'dPen%':>6s}")
    for name, (lo, hi) in cands.items():
        for e in CFG["ebn0_pilot"]:
            r = analyse(lo, hi, e); r["name"] = name; res.append(r)
            print(f"{name:22s} {e:5.0f} {r['Delta']:2d} {r['J_or_mean']:7.4f} {r['eps_plateau']:8.2f} {r['eps_frozen_lo']:8.2f} "
                  f"{r['cond_max']:6.1f} {r['min_abs_H']:6.3f} {r['r1_ber_lo']:9.2e} {r['r1_ber_hi']:9.2e} {100*r['delta_penalty']:6.2f}")
    json.dump(res, open("results/pilot_analytic_L16.json", "w"), indent=1)
