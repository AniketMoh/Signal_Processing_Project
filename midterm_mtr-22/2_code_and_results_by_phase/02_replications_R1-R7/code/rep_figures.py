# rep_figures.py -- figures for the replication report (all from the logs/arrays written by rep1..rep6)
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import norm
import rep2_mathworks as r2, rep4_shahdoosti as r4, rep5_ghanassi as r5, rep6_tracking_theory as r6

C = {'sim': '#1f77b4', 'th': '#d62728', 'alt': '#2ca02c', 'gray': '#555555'}
plt.rcParams.update({'font.size': 10, 'axes.grid': True, 'grid.alpha': 0.3})

# ---- R1
d = np.load('results/rep1_bpsk.npy')
fig, ax = plt.subplots(figsize=(6, 4.2))
x = np.linspace(0, 10.5, 200)
ax.semilogy(x, norm.sf(np.sqrt(2 * 10 ** (x / 10))), color=C['th'], label='theory Q(sqrt(2Eb/N0))')
ax.semilogy(d[:, 0], d[:, 3], 'o', color=C['sim'], label='simulated, numpy Gaussian (2e7 symbols)')
ax.semilogy(d[:, 0], d[:, 5], '-', color=C['alt'], label='exact BER of the 12-uniform (LFSR-type) noise')
ax.semilogy(d[:, 0], np.where(d[:, 7] >= 10, d[:, 6], np.nan), 's', color=C['alt'], mfc='none', label='simulated, LFSR noise (1e7 symbols)')
ax.set_xlabel('Eb/N0 (dB)'); ax.set_ylabel('BER'); ax.set_ylim(1e-7, 0.2); ax.legend(fontsize=8)
ax.set_title('R1  BPSK in AWGN (L1)  [LFSR point at 10 dB omitted: only 1 error]', fontsize=8.5)
fig.tight_layout(); fig.savefig('results/fig_R1_bpsk.png', dpi=150); plt.close(fig)

# ---- R2
rng = np.random.default_rng(2718)
E = np.array([r2.run_once(rng, 'zeros', want_err=True) for _ in range(500)])
fig, ax = plt.subplots(figsize=(6, 4.2))
ax.plot(E.mean(0), color=C['sim'], label='mean |e| over 500 runs (zero initial weights)')
ax.axvline(200, color=C['gray'], ls='--', label='end of training (200 symbols)')
ax.axhline(0.1, color=C['th'], ls=':', label='0.1')
ax.set_xlabel('symbol index'); ax.set_ylabel('|error|'); ax.legend(fontsize=8)
ax.set_title('R2  MathWorks example, 8-tap LMS, mu = 0.1, 30 dB (L1)', fontsize=9)
fig.tight_layout(); fig.savefig('results/fig_R2_mathworks.png', dpi=150); plt.close(fig)

# ---- R4
logf, _, _ = r4.run(False); logq, first, _ = r4.run(True)
fig, ax = plt.subplots(figsize=(6, 4.2))
ax.semilogy([abs(l[1]) for l in logf], color=C['alt'], label='floating point')
ax.semilogy([abs(l[1]) for l in logq], color=C['sim'], label='12 fractional bits, rounding to nearest')
ax.axhline(r4.LSB / (2 * r4.mu * 0.5), color=C['th'], ls=':', label='e_T = 0.0244 (u = 0.5)')
ax.axvline(first, color=C['gray'], ls='--', label=f'all updates zero from iteration {first}')
ax.set_xlim(0, 400); ax.set_ylim(1e-5, 1); ax.set_xlabel('iteration'); ax.set_ylabel('|error|'); ax.legend(fontsize=8)
ax.set_title('R4  stalling of fixed-point LMS (Shahdoosti example)  (small stand-alone fixed-point model, not our L2)', fontsize=9)
fig.tight_layout(); fig.savefig('results/fig_R4_stall.png', dpi=150); plt.close(fig)

# ---- R5
rows = np.load('results/rep5_ghanassi.npy')
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for a, acc, ttl in ((axs[0], 0, 'products rounded before the sum'), (axs[1], 1, 'sum in double precision, rounded once')):
    m = rows[rows[:, 0] == acc]
    mus = m[:, 1]
    a.loglog(mus, m[:, 2], 'o-', color=C['sim'], label='simulation')
    fine = np.geomspace(0.001, 0.18, 200)
    P = np.array([r5.predict(u, bool(acc)) for u in fine])
    a.loglog(fine, P[:, 3], '--', color=C['th'], label='stall formula (Eq. 11, lambda_x = 3.2, lambda_e = 4.5)')
    ok = fine < 0.19
    a.loglog(fine, P[:, 1], ':', color=C['alt'], label='intermediate (Eq. 21 as extracted)')
    a.loglog(fine, P[:, 0], '-.', color=C['gray'], label='stochastic-gradient (Eq. 13)')
    a.set_xlabel('step size mu'); a.set_title(ttl, fontsize=9); a.set_ylim(1e-10, 1e-4)
axs[0].set_ylabel("steady-state squared error"); axs[0].legend(fontsize=7, loc='upper right')
fig.suptitle('R5  fixed-point LMS, N = 100, 16 bit, white input, no noise (Ghanassi et al. setup) (small stand-alone fixed-point model, not our L2)', fontsize=9)
fig.tight_layout(); fig.savefig('results/fig_R5_ghanassi.png', dpi=150); plt.close(fig)

# ---- R6
res = np.load('results/rep6_curves.npy', allow_pickle=True).item()
fig, axs = plt.subplots(1, 3, figsize=(13, 4.2))
for a, kind, ttl in ((axs[0], 0, 'random walk'), (axs[1], 1, 'deterministic ramp')):
    for xi, col in zip([0.0005, 0.002, 0.008], ['#1f77b4', '#ff7f0e', '#9467bd']):
        mus, sim, th = res[str((kind, xi))]
        a.loglog(mus, sim, 'o', color=col, ms=4, label=f'sim xi={xi}')
        a.loglog(mus, th, '-', color=col, lw=1)
    a.set_xlabel('mu'); a.set_ylabel('excess MSE'); a.set_title(ttl + ' (lines: small-step theory)', fontsize=9); a.legend(fontsize=7)
xis = np.array([0.0002, 0.0005, 0.001, 0.002, 0.004, 0.008])
ms0 = [r6.refine_min(*res[str((0, float(x)))][:2])[0] for x in xis]; ms1 = [r6.refine_min(*res[str((1, float(x)))][:2])[0] for x in xis]
th0 = xis / np.sqrt(r6.SV2 * r6.N); th1 = (4 * xis ** 2 / (r6.N * r6.SV2)) ** (1 / 3)
a = axs[2]
a.loglog(xis, ms0, 'o', color='#1f77b4', label='random walk, sim'); a.loglog(xis, th0, '-', color='#1f77b4', label='mu_opt = xi / sqrt(Jmin Tr R)')
a.loglog(xis, ms1, 's', color='#d62728', label='ramp, sim'); a.loglog(xis, th1, '-', color='#d62728', label='mu_opt ~ (4 xi^2/(N Jmin))^(1/3)')
a.minorticks_off(); a.set_xlabel('rms increment per symbol, xi'); a.set_ylabel('optimum mu'); a.legend(fontsize=7); a.set_title('optimum step size', fontsize=9)
fig.tight_layout(); fig.savefig('results/fig_R6_tracking.png', dpi=150); plt.close(fig)
print('figures done')
