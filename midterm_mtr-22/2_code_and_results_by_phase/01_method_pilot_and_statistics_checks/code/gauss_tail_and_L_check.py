"""AUDIT checks (L1, no existing code modified).
(1) Does the numpy Gaussian noise used in all L1 results reproduce Q(sqrt(2Eb/N0)) BELOW 1e-4?  V2 only covered BER >= ~1e-4 (0-8.25 dB).
    Flat channel, direct detector, Eb/N0 = 9, 10, 11 dB, 4e8 bits each, exact Clopper-Pearson 95 % interval.  Seeds 900000+ (unused elsewhere).
(2) Why L = 16?  Analytic Wiener MSE J_min(L) (Delta = 2) on the hardest primary channel state (c = 116) and on c = 40, 16 and 14 dB.
Run from code/: python3 audit/gauss_tail_and_L_check.py"""
import sys; sys.path.insert(0, ".")
import numpy as np
from scipy.stats import binomtest, norm
from config import sigma_from_ebn0
from misadj_lib import wiener
print("(1) flat channel BER, Gaussian generator (lms_lib.make_noise = numpy default_rng.standard_normal)")
for i, e in enumerate((9.0, 10.0, 11.0)):
    sig = sigma_from_ebn0(e); N = 0; k = 0
    rb = np.random.default_rng(900000 + i); rn = np.random.default_rng(910000 + i)
    for _ in range(40):
        n = 10_000_000
        x = 2.0 * rb.integers(0, 2, n) - 1.0; r = x + sig * rn.standard_normal(n)
        k += int(np.sum((r >= 0) != (x > 0))); N += n
    th = norm.sf(np.sqrt(2 * 10 ** (e / 10))); ci = binomtest(k, N, th).proportion_ci(0.95)
    print(f"   {e:4.1f} dB: errors {k:6d} of {N:.1e}  BER {k/N:.3e}  95% CI [{ci.low:.3e}, {ci.high:.3e}]  theory {th:.3e}  inside: {ci.low <= th <= ci.high}")
print("\n(2) analytic J_min(L), Delta = 2 (no simulation)")
for snr in (16.0, 14.0):
    s2 = sigma_from_ebn0(snr) ** 2
    for c in (40, 116):
        h = np.array([1.0, c * 2.0 ** -7, 0.1]); row = []
        for L in (4, 8, 12, 16, 20, 24, 32):
            import misadj_lib; misadj_lib.L = L
            row.append(wiener(h, 2, s2)[1])
        misadj_lib.L = 16
        print(f"   {snr:.0f} dB c={c:3d}: " + "  ".join(f"L={L}: {J:.5f}" for L, J in zip((4, 8, 12, 16, 20, 24, 32), row)))
