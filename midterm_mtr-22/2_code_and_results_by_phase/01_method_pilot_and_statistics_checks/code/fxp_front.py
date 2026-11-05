"""fxp_front.py -- integer FRONT END of the L2 model (new, 23 Oct 2026).  The receivers (fxp_lib.fxp_receivers) are unchanged.
The earlier L2 runs formed r in floating point (channel taps, float noise) and rounded once to s16.12.  This module defines the same
operation in integers, so that RTL can reproduce it bit for bit.  Everything is in units of 2^-16 until the final rounding:
    r_hi    = 65536*x[n] + 512*c[n]*x[n-1] + H2Q*x[n-2] + noise16             (a = c/128, so a*65536 = 512*c exactly)
    noise16 = (sigma_q * noise_int + 32768) >> 16                              sigma_q = round(sigma*65536), noise_int from the LFSR block
    r_q     = clip((r_hi + 8) >> 4, -32768, 32767)                             rounding to s16.12, ties up (same as quantize_signal)
    d_q     = 4096 * x[n-2]                                                    Delta = 2
H2Q = round(0.1 * 65536) = 6554, i.e. h2 = 0.100006 instead of 0.1 (difference 6e-6 of one unit; below 1/40 of an s16.12 LSB).
"""
import numpy as np
from fxp_lib import LFSR_TAPS
from config import sigma_from_ebn0

H2Q = 6554


def lfsr_start_values(seed):
    """Same start values as fxp_lib.lfsr_noise(n, sigma, seed)."""
    rng = np.random.default_rng(seed)
    return [int(rng.integers(1, (1 << int(t[0])) - 1)) for t in LFSR_TAPS]


def noise_int_stream(n, states):
    """Integer noise stream (units 2^-16): sum of the twelve 16-bit words minus 393210, one sample per 16 LFSR steps."""
    st = list(states)
    out = np.zeros(n, dtype=np.int64)
    for i in range(n):
        total = 0
        for j in range(12):
            nn = int(LFSR_TAPS[j, 0]); kk = int(LFSR_TAPS[j, 1])
            word = 0; s = st[j]
            for b in range(16):
                bit = s & 1
                word = (word << 1) | bit
                fb = ((s >> 0) ^ (s >> (nn - kk))) & 1
                s = (s >> 1) | (fb << (nn - 1))
            st[j] = s
            total += word
        out[i] = total - 393210
    return out


def sigma_q_from_ebn0(ebn0_db):
    return int(round(sigma_from_ebn0(ebn0_db) * 65536))


def front_end_int(bits, c, noise_int, sigma_q, h2q=H2Q):
    x = 2 * np.asarray(bits, dtype=np.int64) - 1
    xm1 = np.concatenate([[0], x[:-1]]).astype(np.int64)
    xm2 = np.concatenate([[0, 0], x[:-2]]).astype(np.int64)
    n16 = (sigma_q * noise_int + 32768) >> 16
    rhi = 65536 * x + 512 * np.asarray(c, dtype=np.int64) * xm1 + h2q * xm2 + n16
    r_q = np.clip((rhi + 8) >> 4, -32768, 32767)
    d_q = 4096 * xm2
    return r_q.astype(np.int64), d_q.astype(np.int64)
