"""AUDIT check (L1, small, controlled; existing code NOT modified): Gaussian noise (as used in all L1 results) versus an
FPGA-style bounded noise model = sum of 12 independent U(0,1) minus 6 (Irwin-Hall, variance 1, support +-6 sigma), scaled to the same sigma.
LFSR bit correlations are NOT modelled (numpy uniforms) -- this isolates the effect of the bounded distribution only.
Identical payload bits and identical channel; the two noise models use different random draws. 40 seeds 5400-5439, 14 dB, primary channel.
Run from code/:  python3 audit/noise_model_check.py"""
import sys; sys.path.insert(0, ".")
import numpy as np
from fractions import Fraction
from math import comb, factorial
from exp_lib import *
from lms_lib import triangle_counter, apply_channel, taps_from_counter
from sweep import n_eval_for

def irwin_hall_sf(t, n=12):
    """P(sum of n U(0,1) - n/2 > t) exactly (t in units of the sum's standard deviation = 1 for n=12)."""
    x = Fraction(t).limit_denominator(10**6) + Fraction(n, 2)
    if x >= n: return 0.0
    cdf = sum((-1) ** k * comb(n, k) * (x - k) ** n for k in range(int(x) + 1)) / factorial(n)
    return float(1 - cdf)

from scipy.stats import norm
print("Tail probability P(v > t*sigma):   t    Gaussian      sum-of-12-uniforms   ratio")
for t in (2, 3, 4, 4.5, 5, 5.5):
    g = norm.sf(t); u = irwin_hall_sf(t)
    print(f"                                  {t:4.1f}  {g:10.3e}   {u:10.3e}          {u/g:6.3f}")

snr = 14.0; NT = 30000; seeds = range(5400, 5440)
cases = [("static c=40", None, 40), ("static c=116", None, 116), ("triangle S=20", 20, None), ("triangle S=1000", 1000, None)]
print("\ncase              mu     | R1 BER Gauss / bounded | R3 BER Gauss / bounded (errors) | R3 MSE Gauss / bounded | R2 MSE Gauss / bounded")
for name, S, cfix in cases:
    if S is None:
        ne = 152000; c = np.full(NT + ne, cfix, dtype=np.int64)
    else:
        ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
    taps = taps_from_counter(c, H2); sig = sigma_from_ebn0(snr)
    for mu in (2.0 ** -6, 2.0 ** -8, 2.0 ** -10):
        acc = {m: dict(k1=0, k3=0, J3=0.0, J2=0.0) for m in ("g", "u")}
        N = 0
        for sd in seeds:
            bits = np.concatenate([prbs(NT), make_bits(ne, sd)]).astype(np.int64); x = bpsk(bits); s0 = apply_channel(x, taps)
            rng = np.random.default_rng(sd + 900000)
            noises = {"g": sig * rng.standard_normal(len(x)), "u": sig * (rng.random((len(x), 12)).sum(axis=1) - 6.0)}
            for m, v in noises.items():
                ex = dict(bits=bits, x=x, c=c, taps=taps, r=s0 + v, sigma=sig, N_T=NT, n_total=len(x))
                yA, yF, eA, eF, _ = run_lms(ex, mu, 10 ** 9)
                e1, e2, e3 = ber_indicators(ex, yA, yF)
                acc[m]["k1"] += int(e1[NT:].sum()); acc[m]["k3"] += int(e3[NT:].sum())
                acc[m]["J3"] += float(np.mean(eA[NT:] ** 2)); acc[m]["J2"] += float(np.mean(eF[NT:] ** 2))
            N += ne
        g, u = acc["g"], acc["u"]; ns = len(seeds)
        print(f"{name:17s} 2^{np.log2(mu):<4.0f} | {g['k1']/N:9.2e} / {u['k1']/N:9.2e} | {g['k3']/N:9.2e} / {u['k3']/N:9.2e} ({g['k3']:5d}/{u['k3']:5d}) | {g['J3']/ns:.5f} / {u['J3']/ns:.5f} | {g['J2']/ns:.5f} / {u['J2']/ns:.5f}")
