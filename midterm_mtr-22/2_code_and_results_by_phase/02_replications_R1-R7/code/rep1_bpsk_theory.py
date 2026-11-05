# rep1_bpsk_theory.py -- Replication R1: BPSK in AWGN, BER against the textbook formula Q(sqrt(2 Eb/N0))   [source: Proakis & Salehi, ref. 10]
# Also: exact BER of the FPGA-style noise (sum of 12 uniforms = Irwin-Hall) from theory, compared with the simulated BER.
import sys, time
sys.path.insert(0, '..')
import numpy as np
from scipy.stats import norm, irwinhall
from config import sigma_from_ebn0
from fxp_lib import lfsr_noise

ebn0_list = [0, 2, 4, 6, 8, 9, 10]
N_gauss = 20_000_000          # symbols with numpy Gaussian noise
N_lfsr = 10_000_000           # symbols with the LFSR noise (slower generator)
rng = np.random.default_rng(31415)
out = []
print("Eb/N0  sigma | BER_theory | BER_sim(numpy Gaussian) [errors] | ratio | BER_theory_LFSR | BER_sim(LFSR) [errors] | ratio")
for e in ebn0_list:
    s = sigma_from_ebn0(e)
    th = norm.sf(np.sqrt(2 * 10 ** (e / 10)))
    # x = +1 always is enough for a symmetric channel and symmetric noise (error if noise < -1)
    v = s * rng.standard_normal(N_gauss)
    err_g = int(np.sum(1.0 + v < 0))
    # exact BER for the sum-of-12-uniforms noise: v = s*(S-6), error if s*(S-6) < -1  <=>  S < 6 - 1/s
    thr = 6.0 - 1.0 / s
    th_l = irwinhall.cdf(thr, 12) if thr > 0 else 0.5
    v2 = lfsr_noise(N_lfsr, s, 900 + e)
    err_l = int(np.sum(1.0 + v2 < 0))
    out.append((e, s, th, err_g / N_gauss, err_g, th_l, err_l / N_lfsr, err_l))
    print(f"{e:4d}  {s:.4f} | {th:.3e} | {err_g/N_gauss:.3e} [{err_g}] | {err_g/N_gauss/th:.3f} | {th_l:.3e} | {err_l/N_lfsr:.3e} [{err_l}] | {(err_l/N_lfsr)/th_l if th_l>0 else float('nan'):.3f}   (LFSR theory / Gaussian theory = {th_l/th:.3f})", flush=True)
np.save('results/rep1_bpsk.npy', np.array(out))
