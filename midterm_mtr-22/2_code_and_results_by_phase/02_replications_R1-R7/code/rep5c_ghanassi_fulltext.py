# rep5c_ghanassi_fulltext.py -- R5 rerun after reading the full text of Ghanassi, Champagne, Kabal (2007), supplied 27 Oct 2026.
# The full text shows that the update uses TWO quantisers (their Eqs. 5b, 17): first Q[mu*e'(k)], then dw_l = Q[mu*e'] x'(k-l), then
# Q[dw] is added to the weight (Eq. 5c).  rep5_ghanassi.py rounded mu*e*x once.  Everything else is unchanged (same N, b, input,
# w_o, seeds, iterations).  The formulas are now the paper's exact ones: stall Eq. 11; intermediate Eq. 21 with denominator
# 1 - mu N sx^2 (no /2) and xi_lim (Eq. 16); stochastic gradient Eq. 13 / Table 1 with xi_lim in place of xi_min (Sec. 2.3).
import numpy as np
from numba import njit
import rep5_ghanassi as r5

N, D, SX2, WO2 = r5.N, r5.D, r5.SX2, r5.WO2

@njit(cache=True)
def sim2(mu, n_iter, n_avg, with_acc, seed, wo):
    np.random.seed(seed)
    SC = 32768.0
    wI = np.zeros(N); xI = np.zeros(N)
    tot = 0.0
    for k in range(n_iter):
        for j in range(N - 1, 0, -1):
            xI[j] = xI[j - 1]
        x = np.random.randn() * np.sqrt(0.1)
        xi = np.floor(x * SC + 0.5)
        xI[0] = min(max(xi, -SC), SC - 1)
        y = 0.0
        for j in range(N):
            y += wo[j] * xI[j] / SC
        yI = np.floor(y * SC + 0.5)
        if with_acc:
            s = 0.0
            for j in range(N):
                s += wI[j] * xI[j]
            zI = np.floor(s / SC + 0.5)
        else:
            zI = 0.0
            for j in range(N):
                zI += np.floor(wI[j] * xI[j] / SC + 0.5)
        eI = yI - zI
        qme = np.floor(mu * eI + 0.5)                       # Q[mu e'] in units of D   (Eq. 5b, first quantiser)
        for j in range(N):
            wI[j] += np.floor(qme * xI[j] / SC + 0.5)       # Q[ Q[mu e'] x' ]         (Eqs. 5b/17, 5c)
        if k >= n_iter - n_avg:
            tot += (eI / SC) ** 2
    return tot / n_avg

def formulas(mu, acc):
    S2 = D * D / 12.0; c = 1.0 if acc else float(N); xlim = N * SX2 * S2
    base = xlim + WO2 * S2 + S2 + c * S2
    stall = r5.predict(mu, acc)[3]
    inter = base / (1 - mu * N * SX2) if mu * N * SX2 < 1 else np.nan
    sg = (base + (N / (2 * mu)) * (SX2 * S2 + S2)) / (1 - mu * N * SX2 / 2)
    return stall, inter, sg

if __name__ == '__main__':
    mus = [0.001, 0.002, 0.004, 0.01, 0.02, 0.04, 0.075, 0.1, 0.13, 0.16, 0.18]
    n_iter = 4_000_000; n_avg = n_iter // 4
    rng = np.random.default_rng(1234); wo = rng.standard_normal(N); wo *= np.sqrt(WO2) / np.linalg.norm(wo)
    rows = []
    print("mu | variant | simulated (two quantisers) | stall Eq.11 | intermediate Eq.21 | SG Eq.13 | sim/stall | sim/inter | sim/SG")
    for acc in (0, 1):
        for mu in mus:
            xi = sim2(mu, n_iter, n_avg, bool(acc), 777 + acc, wo)
            st, it, sg = formulas(mu, bool(acc))
            rows.append((acc, mu, xi, st, it, sg))
            print(f"{mu:6.3f} | {'acc' if acc else 'noacc':5s} | {xi:.3e} | {st:.3e} | {it:.3e} | {sg:.3e} | {xi/st:6.2f} | {xi/it if it == it else float('nan'):6.2f} | {xi/sg:6.2f}", flush=True)
    np.save('results/rep5c_ghanassi.npy', np.array(rows))
