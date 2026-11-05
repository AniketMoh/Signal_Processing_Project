# rep5_ghanassi.py -- Replication R5: steady-state squared error of fixed-point LMS, Ghanassi, Champagne, Kabal (Signal Processing 87(12), 2007).
# Setup read from the paper: N = 100 taps, b = 16 bits fractional on [-1,1) (LSB D = 2^-15), white Gaussian input variance 0.1,
# reference y = w_o^T x with ||w_o||^2 = 0.4 and NO noise, rounding to nearest, quantisers on x, y, the products w'x', and mu*e'*x' (Eq. 5a-5c).
# Two variants: 'no accumulator' (each product w'_k x'_k rounded before the sum) and 'accumulator' (sum in double precision, rounded once).
# The paper's formulas are compared with a simulation written from the model description.  The paper's source text is partly unreadable
# (formulas reconstructed from a text extraction), so the predictions below carry that uncertainty.
import sys, numpy as np
from numba import njit

N = 100; B = 16; D = 2.0 ** (1 - B); SX2 = 0.1; WO2 = 0.4

@njit(cache=True)
def sim(mu, n_iter, n_avg, with_acc, seed, wo, ref_unq=False):
    np.random.seed(seed)
    SC = 32768.0                                  # 2^15 = 1/D
    wI = np.zeros(N)                              # weights in units of D (integers stored as floats)
    xI = np.zeros(N)                              # tapped delay line, units of D (quantised input)
    xF = np.zeros(N)                              # same delay line, unquantised (used to build the reference y)
    tot = 0.0
    for k in range(n_iter):
        for j in range(N - 1, 0, -1):
            xI[j] = xI[j - 1]
            xF[j] = xF[j - 1]
        x = np.random.randn() * np.sqrt(0.1)
        xF[0] = x
        xi = np.floor(x * SC + 0.5)
        xI[0] = min(max(xi, -SC), SC - 1)
        # reference y = wo^T x, then y' = Q[y].  Default (ref_unq False): x is the quantised, saturated input, so the model is exactly
        # linear and the paper's formulas apply.  ref_unq True: the unquantised input is used; rare input saturation (|x| > 1, probability 0.16 %)
        # then adds a noise floor of about 1e-5 that the paper's formulas do not contain (see results/rep5_log_v2.txt).
        y = 0.0
        for j in range(N):
            if ref_unq:
                y += wo[j] * xF[j]
            else:
                y += wo[j] * xI[j] / SC
        yI = np.floor(y * SC + 0.5)
        # filter output
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
        for j in range(N):
            dw = np.floor(mu * eI * xI[j] / SC + 0.5)
            wI[j] += dw
        if k >= n_iter - n_avg:
            tot += (eI / SC) ** 2
    return tot / n_avg

def predict(mu, with_acc):
    S2 = D * D / 12.0
    c = 1.0 if with_acc else float(N)
    Sx = Sy = Sw = Sme = Sdw = S2
    Swx = c * S2
    sg = (1.0 / (1 - mu * N * SX2 / 2)) * (WO2 * Sx + Sy + Swx + (N / (2 * mu)) * (SX2 * Sme + Sdw)) if mu * N * SX2 / 2 < 1 else np.nan
    xlim = N * SX2 * Sw
    im_a = (1.0 / (1 - mu * N * SX2)) * (xlim + WO2 * Sx + Sy + Swx) if mu * N * SX2 < 1 else np.nan        # as extracted (no /2)
    im_b = (1.0 / (1 - mu * N * SX2 / 2)) * (xlim + WO2 * Sx + Sy + Swx)                                   # with /2
    lx, le = 3.2, 4.5
    stall = D * D / (le * le * mu * mu) * (np.floor(1.0 / (2 * lx * np.sqrt(SX2))) + 0.5) ** 2
    return sg, im_a, im_b, stall

if __name__ == '__main__':
    mus = [0.001, 0.002, 0.004, 0.01, 0.02, 0.04, 0.075, 0.1, 0.13, 0.16, 0.18]
    n_iter = int(sys.argv[1]) if len(sys.argv) > 1 else 4_000_000
    n_avg = n_iter // 4
    rng = np.random.default_rng(1234)
    wo = rng.standard_normal(N); wo *= np.sqrt(WO2) / np.linalg.norm(wo)
    print("D =", D, " D^2/12 =", D * D / 12, " stability bound 2/(N sx2) =", 2 / (N * SX2))
    print("mu | variant | simulated xi' | SG (Eq.13) | intermediate (Eq.21 as extracted) | interm. (with /2) | stall (Eq.11, lx=3.2 le=4.5)")
    rows = []
    for acc in (0, 1):
        for mu in mus:
            xi = sim(mu, n_iter, n_avg, bool(acc), 777 + acc, wo)
            sg, ia, ib, st = predict(mu, bool(acc))
            rows.append((acc, mu, xi, sg, ia, ib, st))
            print(f"{mu:6.3f} | {'acc' if acc else 'noacc':5s} | {xi:.3e} | {sg:.3e} | {ia:.3e} | {ib:.3e} | {st:.3e}", flush=True)
    np.save('results/rep5_ghanassi.npy', np.array(rows))
