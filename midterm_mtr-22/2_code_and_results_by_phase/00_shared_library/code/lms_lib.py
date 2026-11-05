# lms_lib.py -- building blocks for the LMS tracking study (floating point, L1)
# Written in a plain style: small functions, loops instead of tricks, comments on every step.
import numpy as np
from scipy.stats import norm

try:                                   # numba only makes the loop faster; the code also runs without it
    from numba import njit
except ImportError:
    def njit(f=None, **kw):
        return f if f is not None else (lambda g: g)

from config import CFG, DA, sigma_from_ebn0


# ---------------------------------------------------------------- transmitter
def make_bits(n, seed):
    """Random payload bits 0/1 (seeded, so the same seed gives the same bits)."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, n)


def lfsr_bits(n, nbits=15, taps=(15, 14), seed=1):
    """Maximal-length LFSR (PRBS). Output bit = lowest bit of the shift register."""
    state = seed
    out = np.zeros(n, dtype=np.int64)
    for i in range(n):
        out[i] = state & 1
        fb = 0
        for t in taps:                       # polynomial term x^t -> register bit (nbits - t)
            fb ^= (state >> (nbits - t)) & 1
        state = (state >> 1) | (fb << (nbits - 1))
    return out


def bpsk(bits):
    """b in {0,1} -> x = 2b - 1 in {-1,+1}."""
    return 2.0 * np.asarray(bits, dtype=float) - 1.0


# ---------------------------------------------------------------- channel
def triangle_counter(n_total, N_T, c_lo, c_hi, S):
    """Integer counter c[n] of the channel coefficient a[n] = c[n]*DA.
    Static at c_lo for n < N_T. From n = N_T it goes up c_lo -> c_hi -> c_lo ... by 1 every S symbols.
    S = None means a static channel."""
    c = np.full(n_total, c_lo, dtype=np.int64)
    if S is None:
        return c
    steps = c_hi - c_lo
    n = np.arange(N_T, n_total)
    k = (n - N_T) // S                       # how many updates have happened
    idx = k % (2 * steps)                    # position inside one up-down period
    c[N_T:] = c_lo + np.where(idx <= steps, idx, 2 * steps - idx)
    return c


def taps_from_counter(c, h2=0.1):
    """Channel taps for every time: [1, a[n], h2]  -> array shape (n, 3)."""
    taps = np.zeros((len(c), 3))
    taps[:, 0] = 1.0
    taps[:, 1] = c * DA
    taps[:, 2] = h2
    return taps


def apply_channel(x, taps):
    """r[n] = sum_k taps[n,k] * x[n-k]   (x before n=0 is zero)."""
    n_total, M = taps.shape
    r = np.zeros(n_total)
    for k in range(M):
        r[k:] += taps[k:, k] * x[:n_total - k]
    return r


def make_noise(n, sigma, seed):
    rng = np.random.default_rng(seed)
    return sigma * rng.standard_normal(n)


# ---------------------------------------------------------------- receivers
@njit(cache=True)
def lms_receivers(r, d, L, mu, N_T, mode, hist_stride):
    """R3 (adaptive) and R2 (frozen after N_T) run on the same received samples.
    r : received samples          d : desired symbols, d[n] = x[n - Delta]
    mode 0 = supervised after training, mode 1 = decision-directed after training
    Before N_T both receivers are the same filter (training with the known sequence).
    Returns the output and a-priori error of R3 and R2, plus the coefficients of R3 every hist_stride symbols."""
    n_total = len(r)
    wA = np.zeros(L)                  # adaptive coefficients (R3)
    wF = np.zeros(L)                  # frozen copy (R2)
    u = np.zeros(L)                   # tapped delay line
    yA = np.zeros(n_total)
    yF = np.zeros(n_total)
    eA = np.zeros(n_total)
    eF = np.zeros(n_total)
    n_hist = n_total // hist_stride
    wH = np.zeros((n_hist, L))
    for n in range(n_total):
        for k in range(L - 1, 0, -1):          # shift the delay line
            u[k] = u[k - 1]
        u[0] = r[n]
        if n == N_T:                           # freeze: w_F = w[N_T]
            for k in range(L):
                wF[k] = wA[k]
        ya = 0.0
        for k in range(L):
            ya += wA[k] * u[k]
        if n < N_T:
            yf = ya
        else:
            yf = 0.0
            for k in range(L):
                yf += wF[k] * u[k]
        if n >= N_T and mode == 1:             # decision-directed reference
            ref = 1.0 if ya >= 0.0 else -1.0
        else:
            ref = d[n]
        e = ref - ya                           # error used for the update
        yA[n] = ya
        yF[n] = yf
        eA[n] = d[n] - ya                      # error against the TRUE symbol (for MSE)
        eF[n] = d[n] - yf
        for k in range(L):                     # LMS update: w = w + mu * e * u
            wA[k] += mu * e * u[k]
        if (n % hist_stride) == 0 and (n // hist_stride) < n_hist:
            for k in range(L):
                wH[n // hist_stride, k] = wA[k]
    return yA, yF, eA, eF, wH


def delayed_symbols(x, Delta):
    """d[n] = x[n - Delta]  (zero before the start)."""
    d = np.zeros(len(x))
    d[Delta:] = x[:len(x) - Delta]
    return d


def count_errors(y, bits, delay, start, stop):
    """Hard decision b_hat[n] = 1 if y[n] >= 0.  y[n] is compared with bits[n - delay]."""
    n = np.arange(start, stop)
    est = (y[n] >= 0).astype(np.int64)
    err = int(np.sum(est != bits[n - delay]))
    return err, stop - start


def make_experiment(S, c_range, ebn0_db, seed, N_T=None, N_eval=None, training="prbs"):
    """Everything the three receivers need. The bits, the noise and the trajectory depend ONLY on
    (seed, S, c_range, ebn0): the receiver settings (mu, Delta, L) never change them -> fair comparison."""
    N_T = CFG["N_T"] if N_T is None else N_T
    N_eval = CFG["N_eval"] if N_eval is None else N_eval
    n_total = N_T + N_eval
    if training == "prbs":
        tr_bits = lfsr_bits(N_T, CFG["prbs_nbits"], CFG["prbs_taps"], CFG["prbs_seed"])
    else:                                       # alternating 0,1,0,1 (negative control)
        tr_bits = np.arange(N_T) % 2
    pay_bits = make_bits(N_eval, seed)
    bits = np.concatenate([tr_bits, pay_bits]).astype(np.int64)
    x = bpsk(bits)
    c = triangle_counter(n_total, N_T, c_range[0], c_range[1], S)
    taps = taps_from_counter(c, CFG["h2"])
    sigma = sigma_from_ebn0(ebn0_db)
    v = make_noise(n_total, sigma, seed + 500000)
    r = apply_channel(x, taps) + v
    return dict(bits=bits, x=x, c=c, taps=taps, r=r, sigma=sigma, N_T=N_T, n_total=n_total)


def run_receivers(exp, Delta, mu, mode=0, hist_stride=64):
    """Runs R1, R2, R3 on one experiment. R1 is the direct detector (delay = index of dominant tap = 0)."""
    L = CFG["L"]
    d = delayed_symbols(exp["x"], Delta)
    yA, yF, eA, eF, wH = lms_receivers(exp["r"], d, L, mu, exp["N_T"], mode, hist_stride)
    return dict(y1=exp["r"], y2=yF, y3=yA, e2=eF, e3=eA, wH=wH, hist_stride=hist_stride, Delta=Delta)


# ---------------------------------------------------------------- oracle (analysis tool, not a receiver)
def oracle_at(taps, n, L, Delta, sigma2, quasi_static=False):
    """Best possible L-tap equalizer at time n if the channel is known.
    Exact version: row j of H uses the taps that were really active at time n-j (the channel moves
    inside the observation window).  quasi_static=True pretends all rows use the taps at time n.
    Returns (w_oracle, J_oracle)."""
    M = taps.shape[1]
    H = np.zeros((L, L + M - 1))
    for j in range(L):
        t = n if quasi_static else n - j
        for k in range(M):
            H[j, j + k] = taps[t, k]
    p = H[:, Delta]                              # cross-correlation of u with x[n - Delta]
    R = H @ H.T + sigma2 * np.eye(L)
    w = np.linalg.solve(R, p)
    return w, 1.0 - p @ w


def oracle_mean(taps, n0, n1, L, Delta, sigma2, stride=8):
    """Mean oracle MSE over n0..n1 (every `stride`-th symbol)."""
    J = [oracle_at(taps, n, L, Delta, sigma2)[1] for n in range(n0, n1, stride)]
    return float(np.mean(J))


def r1_exact_ber(a, h2, sigma):
    """Exact BER of the direct detector on [1, a, h2] (4 ISI patterns, Gaussian noise)."""
    b = 0.0
    for s1 in (1, -1):
        for s2 in (1, -1):
            b += 0.25 * norm.sf((1 + a * s1 + h2 * s2) / sigma)
    return b


def bpsk_theory(ebn0_db):
    return norm.sf(np.sqrt(2 * 10.0 ** (ebn0_db / 10.0)))
