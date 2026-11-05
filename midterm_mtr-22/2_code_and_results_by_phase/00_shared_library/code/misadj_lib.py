# misadj_lib.py -- tools for the misadjustment investigation (floating point, L1).
# Nothing here changes the LMS algorithm: the LMS loop is lms_lib.lms_receivers, used as it is.
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from config import CFG, sigma_from_ebn0
from lms_lib import lms_receivers, delayed_symbols, make_noise, apply_channel

try:
    from numba import njit
except ImportError:
    def njit(f=None, **kw):
        return f if f is not None else (lambda g: g)

L = CFG["L"]


def assemble_H(h, L, M=None):
    M = len(h)
    H = np.zeros((L, L + M - 1))
    for j in range(L):
        for k in range(M):
            H[j, j + k] = h[k]
    return H


def wiener(h, Delta, s2):
    """Static channel h: Wiener coefficients, minimum MSE J_min, input correlation matrix R."""
    H = assemble_H(h, L)
    R = H @ H.T + s2 * np.eye(L)
    p = H[:, Delta].copy()
    w = np.linalg.solve(R, p)
    return w, 1.0 - p @ w, R


def simulate_static(h, N, seed, sigma, gaussian=False):
    """x (binary or Gaussian), received samples r = h*x + v, for a static channel."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(N) if gaussian else 2.0 * rng.integers(0, 2, N) - 1.0
    taps = np.tile(np.array(h, dtype=float), (N, 1))
    r = apply_channel(x, taps) + make_noise(N, sigma, seed + 777)
    return x, r


def run_lms(r, x, Delta, mu):
    """Runs the project's LMS loop (unchanged) and returns the a-priori error e[n] = x[n-Delta] - y[n]."""
    d = delayed_symbols(x, Delta)
    n = len(r)
    yA, yF, eA, eF, wH = lms_receivers(r, d, L, mu, n + 5, 0, n + 5)
    return eA


def input_matrix(r):
    """U[n, i] = r[n-i]  (rows are the tapped delay line u(n))."""
    pad = np.concatenate([np.zeros(L - 1), r])
    return np.ascontiguousarray(sliding_window_view(pad, L)[:, ::-1])


def wiener_error(r, x, w, Delta):
    """e_o[n] = x[n-Delta] - w_o^T u(n): the error of the FIXED optimal filter (no adaptation)."""
    U = input_matrix(r)
    return delayed_symbols(x, Delta) - U @ w, U


def gradient_noise_sums(e_o, r, kmax=100, skip=500):
    """C(j) = E[ e_o(n) e_o(n-j) u(n)^T u(n-j) ],  j = 0..kmax   (trace of the gradient-noise autocovariance).
    u(n)^T u(n-j) = sum_{i<L} r[n-i] r[n-i-j] is a moving sum of r[m] r[m-j]."""
    N = len(r)
    C = np.zeros(kmax + 1)
    for j in range(kmax + 1):
        z = np.zeros(N)
        z[j:] = r[j:] * r[: N - j]
        cs = np.cumsum(z)
        P = cs.copy()
        P[L:] = cs[L:] - cs[:-L]               # moving sum over the L most recent products
        n0 = skip + j
        C[j] = np.mean(e_o[n0:] * e_o[n0 - j : N - j] * P[n0:])
    return C


def textbook_excess(mu, trR):
    x = mu * trR / 2.0
    return x / (1.0 - x)                       # in units of J_min


@njit(cache=True)
def linearised_mse(U, e_o, R, mu, burn):
    """First-order model of LMS: the update uses the AVERAGE matrix R instead of u u^T,
         wt(n+1) = wt(n) - mu R wt(n) + mu e_o(n) u(n),      error e(n) = e_o(n) - u(n)^T wt(n).
    Returns the mean of e(n)^2 after `burn` symbols."""
    N, Lc = U.shape
    wt = np.zeros(Lc)
    acc = 0.0
    cnt = 0
    for n in range(N):
        y = 0.0
        for i in range(Lc):
            y += U[n, i] * wt[i]
        e = e_o[n] - y
        if n >= burn:
            acc += e * e
            cnt += 1
        for i in range(Lc):
            s = 0.0
            for k in range(Lc):
                s += R[i, k] * wt[k]
            wt[i] += -mu * s + mu * e_o[n] * U[n, i]
    return acc / cnt


@njit(cache=True)
def lms_rows(U, d, mu):
    """Same update rule as the project LMS (w += mu*e*u, a-priori error) but applied to pre-built input
    rows U[n,:] and desired values d[n]. Used (a) to cross-check the project loop and (b) on row-shuffled
    data, where the textbook independence assumption holds by construction."""
    N, Lc = U.shape
    w = np.zeros(Lc)
    e = np.zeros(N)
    for n in range(N):
        y = 0.0
        for i in range(Lc):
            y += w[i] * U[n, i]
        e[n] = d[n] - y
        for i in range(Lc):
            w[i] += mu * e[n] * U[n, i]
    return e


def _fourth(a, b, c, d, s, kap):
    """E[(a.z)(b.z)(c.z)(d.z)] for independent zero-mean z_k with variances s_k and fourth cumulants kap_k."""
    return (np.sum(kap * a * b * c * d)
            + np.sum(s * a * b) * np.sum(s * c * d)
            + np.sum(s * a * c) * np.sum(s * b * d)
            + np.sum(s * a * d) * np.sum(s * b * c))


def exact_C(h, w, Delta, s2, jmax=60, kx=-2.0):
    """Exact C(j) = E[ e_o(n) e_o(n-j) u(n)^T u(n-j) ],  j = 0..jmax,
    for data of variance 1 and fourth cumulant kx (binary +-1: kx = -2; Gaussian: kx = 0) and Gaussian noise
    of variance s2.  e_o(n) = x[n-Delta] - w^T u(n) is the error of the FIXED Wiener filter.  Pure algebra,
    no simulation: every signal is a linear form in independent variables and the fourth moment of four
    linear forms is known exactly."""
    M = len(h)
    T = L + M + jmax + L + Delta + 5
    s = np.concatenate([np.ones(T), s2 * np.ones(T)])
    kap = np.concatenate([kx * np.ones(T), np.zeros(T)])

    def rho(p):                                   # r at time -p
        v = np.zeros(2 * T)
        for k in range(M):
            v[p + k] = h[k]
        v[T + p] = 1.0
        return v

    def eo(p):                                    # e_o at time -p
        v = np.zeros(2 * T)
        v[p + Delta] += 1.0
        for i in range(L):
            v -= w[i] * rho(p + i)
        return v

    e0 = eo(0)
    C = np.zeros(jmax + 1)
    for j in range(jmax + 1):
        ej = eo(j)
        C[j] = sum(_fourth(e0, ej, rho(i), rho(i + j), s, kap) for i in range(L))
    return C


def first_order_excess(mu, C):
    """J_ex = (mu/2) * ( C(0) - 2*sum_{j>=1} C(j) )   (first order in mu, correlated residual error)."""
    return 0.5 * mu * (C[0] - 2.0 * C[1:].sum())
