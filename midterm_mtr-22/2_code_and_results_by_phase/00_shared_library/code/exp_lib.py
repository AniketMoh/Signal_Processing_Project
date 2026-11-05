# exp_lib.py -- experiment builders and analysis helpers for P2 (abrupt transition) and P3 (continuous variation).
# The LMS loop itself is lms_lib.lms_receivers and is NOT changed.
import numpy as np
from functools import lru_cache
from config import CFG, DA, sigma_from_ebn0
from lms_lib import (lfsr_bits, bpsk, make_bits, make_noise, apply_channel, taps_from_counter,
                     triangle_counter, delayed_symbols, lms_receivers, r1_exact_ber)
from misadj_lib import wiener, exact_C, first_order_excess

L, M, H2 = CFG["L"], CFG["M"], CFG["h2"]
DELTA = 2                                  # Dfix from V5 (provisional)


@lru_cache(maxsize=4)
def prbs(n):
    return lfsr_bits(n, CFG["prbs_nbits"], CFG["prbs_taps"], CFG["prbs_seed"])


def make_exp_from_counter(c, N_T, ebn0_db, seed):
    """Same data/noise convention as lms_lib.make_experiment: PRBS training, random payload, noise seed+500000."""
    n_total = len(c)
    bits = np.concatenate([prbs(N_T), make_bits(n_total - N_T, seed)]).astype(np.int64)
    x = bpsk(bits)
    taps = taps_from_counter(c, H2)
    sigma = sigma_from_ebn0(ebn0_db)
    r = apply_channel(x, taps) + make_noise(n_total, sigma, seed + 500000)
    return dict(bits=bits, x=x, c=c, taps=taps, r=r, sigma=sigma, N_T=N_T, n_total=n_total)


def step_counter(cA, cB, N_T, N_pre, N_post):
    """Static cA for n < N_C = N_T + N_pre, then static cB. R2 freezes at N_T (during the pre-transition period)."""
    c = np.full(N_T + N_pre + N_post, cA, dtype=np.int64)
    c[N_T + N_pre:] = cB
    return c


def run_lms(exp, mu, hist_stride, mode=0):
    d = delayed_symbols(exp["x"], DELTA)
    return lms_receivers(exp["r"], d, L, mu, exp["N_T"], mode, hist_stride)   # yA, yF, eA, eF, wH


def ber_indicators(exp, yA, yF):
    """Per-symbol error indicators for R1 (delay 0), R2/R3 (delay DELTA). Aligned as in V3."""
    n = exp["n_total"]; bits = exp["bits"]
    e1 = ((exp["r"] >= 0).astype(np.int64) != bits).astype(np.int8)
    ref = np.zeros(n, dtype=np.int64); ref[DELTA:] = bits[:n - DELTA]
    e2 = ((yF >= 0).astype(np.int64) != ref).astype(np.int8)
    e3 = ((yA >= 0).astype(np.int64) != ref).astype(np.int8)
    return e1, e2, e3


def Rp_const(c, s2):
    """R, p, J_min and Wiener filter for the static channel with counter c."""
    h = np.array([1.0, c * DA, H2])
    w, J, R = wiener(h, DELTA, s2)
    H = np.zeros((L, L + M - 1))
    for j in range(L):
        for k in range(M):
            H[j, j + k] = h[k]
    return w, J, R, H[:, DELTA].copy()


def oracle_J_series(taps, n0, n1, s2, chunk=4000):
    """Exact instantaneous-channel oracle MSE J_or[n] for n0 <= n < n1 (row j of H uses taps at n-j). Batched."""
    out = np.zeros(n1 - n0)
    j_idx = np.arange(L)
    for a in range(n0, n1, chunk):
        b = min(a + chunk, n1)
        n = np.arange(a, b)
        Hm = np.zeros((len(n), L, L + M - 1))
        for k in range(M):
            tk = taps[n[:, None] - j_idx[None, :], k]                 # (len, L)
            Hm[:, j_idx, j_idx + k] = tk
        p = Hm[:, :, DELTA]
        R = np.einsum("nij,nkj->nik", Hm, Hm) + s2 * np.eye(L)[None]
        w = np.linalg.solve(R, p[:, :, None])[:, :, 0]
        out[a - n0: b - n0] = 1.0 - np.einsum("ni,ni->n", p, w)
    return out


def fixed_filter_mse_series(taps, n0, n1, s2, wfix, chunk=4000):
    """Exact MSE of a FIXED filter wfix on the moving channel: 1 - 2 w.p + w R w, row j using taps at n-j."""
    out = np.zeros(n1 - n0)
    j_idx = np.arange(L)
    for a in range(n0, n1, chunk):
        b = min(a + chunk, n1)
        n = np.arange(a, b)
        Hm = np.zeros((len(n), L, L + M - 1))
        for k in range(M):
            Hm[:, j_idx, j_idx + k] = taps[n[:, None] - j_idx[None, :], k]
        p = Hm[:, :, DELTA]
        Hw = np.einsum("nij,i->nj", Hm, wfix)
        out[a - n0: b - n0] = 1.0 - 2.0 * p @ wfix + np.einsum("nj,nj->n", Hw, Hw) + s2 * wfix @ wfix
    return out


def plateau_stats(c_lo, c_hi, s2):
    """eps_plateau (best single fixed filter for the time-averaged channel, quasi-static, triangle weights),
    eps_frozen_lo (filter trained at c_lo), J_or_mean; all at DELTA."""
    cs = np.arange(c_lo, c_hi + 1)
    wgt = np.ones(len(cs)); wgt[0] = wgt[-1] = 0.5; wgt /= wgt.sum()
    Rs = 0; ps = 0; Jor = []
    for i, c in enumerate(cs):
        w, J, R, p = Rp_const(c, s2)
        Rs = Rs + wgt[i] * R; ps = ps + wgt[i] * p; Jor.append(J)
    wbar = np.linalg.solve(Rs, ps)
    w0 = Rp_const(c_lo, s2)[0]
    def Jof(w):
        return float(sum(wgt[i] * (1 - 2 * w @ Rp_const(c, s2)[3] + w @ Rp_const(c, s2)[2] @ w) for i, c in enumerate(cs)))
    Jm = float(np.dot(wgt, Jor))
    return dict(J_or_mean=Jm, eps_plateau=Jof(wbar) / Jm - 1, eps_frozen_lo=Jof(w0) / Jm - 1, wbar=wbar)


def boot_ci(v, B=400, seed=0, stat=np.mean):
    """95 % bootstrap percentile interval of stat(v) over seeds."""
    v = np.asarray(v, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), (B, len(v)))
    s = np.array([stat(v[i]) for i in idx])
    return float(stat(v)), float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))
