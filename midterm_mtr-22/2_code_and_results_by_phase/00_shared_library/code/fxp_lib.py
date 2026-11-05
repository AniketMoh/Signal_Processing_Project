"""fxp_lib.py -- P6a, level L2: bit-true FIXED-POINT model of the receivers (and an FPGA-style noise generator).
The LMS equations are the SAME as in lms_lib.lms_receivers (L1):  y = w.u,  e = d - y,  w <- w + mu*e*u,  R2 = copy of w at N_T.
Only the arithmetic is finite precision.  Every format, product width, rounding rule and saturation is stated below.

Notation sN.F = signed two's-complement word of N bits with F fractional bits; range [-2^(N-1-F), 2^(N-1-F) - 2^-F], LSB = 2^-F.

  signal                      format                         rule
  received sample r, u[k]     s16.12   (range +-8)          round to nearest from the channel+noise value, saturate
  desired symbol d            s16.12   (+-1 = +-4096)       exact
  coefficient accumulator     s(B_acc).(B_acc-2)  (+-2)     updates added here; saturate
  multiplier coefficient      s(B_mul).(B_mul-2)  (+-2)     = B_mul most significant bits of the accumulator, rounded (rule below), saturate
  filter product w*u          (B_mul+16) bits, frac (B_mul-2)+12      exact (no rounding)
  adder tree (16 products)    (B_mul+20) bits, same frac               exact (4 guard bits)
  output y                    s16.12   round from the adder tree, saturate
  error e = d - y             s16.12   saturate (computed exactly first)
  update product e*u          32 bits, frac 24              exact
  mu = 2^-p                   arithmetic shift right by p   (power-of-two step sizes only, as in the FPGA)
  update added to w           rounded from frac 24+p to the accumulator LSB (frac B_acc-2); exact if B_acc-2 >= 24+p
Rounding rule (parameter `rnd`): 1 = round to nearest (ties upward: floor(x + 1/2)), 0 = truncation (floor, toward -infinity).
Dynamic range check (20 Oct): |w_Wiener| <= 0.987 over all channel states and 12-16 dB; |w| <= 1.10 in LMS runs with jumps and S = 1
at mu up to 2^-5; |r| <= 2.73; |y|, |e| <= 3.73 -> +-2 for coefficients and +-8 for signals leave headroom.
Decision rule: b_hat = 1 if y >= 0 (on the rounded y), exactly as L1.
"""
import numpy as np
from numba import njit

FR = 12                                   # fractional bits of r, u, y, e (s16.12)
W16_MIN, W16_MAX = -(1 << 15), (1 << 15) - 1


@njit(cache=True)
def sat(x, nbits):
    lo = -(1 << (nbits - 1)); hi = (1 << (nbits - 1)) - 1
    return lo if x < lo else (hi if x > hi else x)


@njit(cache=True)
def rshift(x, s, rnd):
    """x * 2^-s on integers: round to nearest (rnd=1) or truncate toward -inf (rnd=0).  s >= 0."""
    if s <= 0:
        return x << (-s)
    if rnd == 1:
        return (x + (1 << (s - 1))) >> s
    return x >> s


def quantize_signal(v):
    """float array -> s16.12 integers (round to nearest, saturate)."""
    q = np.floor(np.asarray(v) * (1 << FR) + 0.5).astype(np.int64)
    return np.clip(q, W16_MIN, W16_MAX)


@njit(cache=True)
def fxp_receivers(r_q, d_q, L, p, N_T, B_mul, B_acc, rnd, hist_stride):
    """Bit-true R3 (adaptive) and R2 (frozen at N_T), supervised, mu = 2^-p.
    r_q, d_q : int64 arrays in s16.12.  Returns yA, yF, eA, eF (integers, s16.12), coefficient history of the MULTIPLIER
    coefficients of R3 (as floats), and counters: number of nonzero exact updates that were rounded to zero (stalls), total updates."""
    n_total = len(r_q)
    FA = B_acc - 2; FM = B_mul - 2
    acc = np.zeros(L, np.int64)            # R3 accumulator
    wm = np.zeros(L, np.int64)             # R3 multiplier coefficients
    wf = np.zeros(L, np.int64)             # R2 frozen multiplier coefficients
    u = np.zeros(L, np.int64)
    yA = np.zeros(n_total, np.int64); yF = np.zeros(n_total, np.int64)
    eA = np.zeros(n_total, np.int64); eF = np.zeros(n_total, np.int64)
    n_hist = n_total // hist_stride
    wH = np.zeros((n_hist, L))
    stalls = 0; updates = 0
    for n in range(n_total):
        for k in range(L - 1, 0, -1):
            u[k] = u[k - 1]
        u[0] = r_q[n]
        for k in range(L):                                       # multiplier coefficients = rounded MSBs of the accumulator
            wm[k] = sat(rshift(acc[k], FA - FM, rnd), B_mul)
        if n == N_T:
            for k in range(L):
                wf[k] = wm[k]
        s = 0
        for k in range(L):
            s += wm[k] * u[k]                                    # exact products and exact sum (frac FM+12)
        ya = sat(rshift(s, FM, rnd), 16)
        if n < N_T:
            yf = ya
        else:
            s2 = 0
            for k in range(L):
                s2 += wf[k] * u[k]
            yf = sat(rshift(s2, FM, rnd), 16)
        e = sat(d_q[n] - ya, 16)
        yA[n] = ya; yF[n] = yf; eA[n] = e; eF[n] = sat(d_q[n] - yf, 16)
        for k in range(L):                                       # LMS update w <- w + mu*e*u
            t = e * u[k]                                         # frac 2*FR = 24, exact
            sh = 2 * FR + p - FA                                 # shift from frac 24+p to frac FA
            dlt = rshift(t, sh, rnd) if sh > 0 else (t << (-sh))
            if t != 0:
                updates += 1
                if dlt == 0:
                    stalls += 1
            acc[k] = sat(acc[k] + dlt, B_acc)
        if (n % hist_stride) == 0 and (n // hist_stride) < n_hist:     # recorded AFTER the update, as in L1 (lms_lib line 124-126)
            for k in range(L):
                wH[n // hist_stride, k] = sat(rshift(acc[k], FA - FM, rnd), B_mul) / (1 << FM)
    return yA, yF, eA, eF, wH, stalls, updates


# ------------------------------------------------------------------ FPGA-style noise generator (PPR-22 Sec. 4.3)
# 12 separate Fibonacci LFSRs with distinct trinomials x^n + x^k + 1 (maximal-length taps as listed in Xilinx XAPP052; primitivity is
# verified in p6a_tests.py T5).  Each LFSR produces 16 fresh bits per noise sample -> u_i = (word + 1/2) / 2^16 in (0,1).
# v = sigma * (sum_{i=1..12} u_i - 6): mean 0, variance sigma^2 (minus a 2^-32-size quantisation term), support +-6 sigma (Irwin-Hall).
LFSR_TAPS = np.array([[17, 14], [18, 11], [20, 17], [21, 19], [22, 21], [23, 18], [25, 22], [28, 25], [29, 27], [31, 28], [33, 20], [35, 33]], np.int64)


@njit(cache=True)
def _lfsr_noise(n, taps, states):
    out = np.zeros(n)
    m = taps.shape[0]
    for i in range(n):
        tot = 0.0
        for j in range(m):
            nb = taps[j, 0]; kb = taps[j, 1]; st = states[j]; word = 0
            for b in range(16):
                bit = st & 1
                word = (word << 1) | bit
                fb = ((st >> (nb - nb)) ^ (st >> (nb - kb))) & 1     # x^n -> register bit 0, x^k -> bit (n-k)  (lms_lib convention)
                st = (st >> 1) | (fb << (nb - 1))
            states[j] = st
            tot += (word + 0.5) / 65536.0
        out[i] = tot - 6.0
    return out


def lfsr_noise(n, sigma, seed):
    """FPGA-style noise, n samples, standard deviation sigma.  Seeds of the 12 LFSRs are derived from `seed` (never all-zero)."""
    rng = np.random.default_rng(seed)
    states = np.array([int(rng.integers(1, (1 << int(t[0])) - 1)) for t in LFSR_TAPS], np.int64)
    return sigma * _lfsr_noise(n, LFSR_TAPS, states)
