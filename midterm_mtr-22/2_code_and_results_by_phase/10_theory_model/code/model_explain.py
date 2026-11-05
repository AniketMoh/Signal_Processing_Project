"""model_explain.py -- why the boundary obeys S*.mu = const, and why the optimum-step exponent is below 2/3 (uses model_boundary.py).
Analytic/deterministic computations only (no LMS runs).
  (1) Time scaling: the lag part of the mean-weight model depends on mu and S almost only through x = mu*S  -> collapse check.
  (2) Continuous boundary x* = mu*S at rho = 0.5 (fine S scan) for each channel and SNR.
  (3) Pure-ramp steady-state lag (PPR-22's 2/3 argument): eps_ramp = K / x^2 with K = mean_c (dw*/dc)^T R^-1 (dw*/dc) / J_or.
      Compared with the full model at the optimum: how much of the 'missing' lag comes from not reaching steady state.
  (4) Eigenvalues of R along the trajectories and the number of adaptation time constants per half period at the optimum.
  (5) Exponent rule: if eps_lag ~ x^-q near the optimum and eps_gn ~ mu, then mu_opt ~ S^(-q/(q+1)).
Outputs results/model/explain_log.txt, explain.json, fig_model_*.png"""
import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from config import CFG, DA, sigma_from_ebn0
from lms_lib import triangle_counter
from exp_lib import Rp_const
from model_boundary import lag_excess, gn_per_state, NT, L, DELTA
OUT = "results/model"; log = open(f"{OUT}/explain_log.txt", "w")
def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()
res = {}

def Jor_mean(lo, hi, s2, S, ne):
    c = triangle_counter(NT + ne, NT, lo, hi, S); w = np.bincount(c[NT:] - lo, minlength=hi - lo + 1) / ne
    return float(sum(w[i] * Rp_const(lo + i, s2)[1] for i in range(hi - lo + 1)))   # quasi-static approximation of the oracle mean

for tag, lo, hi, snr in (("primary_16", 40, 116, 16.0), ("primary_14", 40, 116, 14.0), ("control_16", 26, 77, 16.0), ("control_14", 26, 77, 14.0)):
    s2 = sigma_from_ebn0(snr) ** 2; A = json.load(open(f"results/final/analysis_{tag}.json")); plat = A["plateau"]
    w0 = Rp_const(lo, s2)[0]; gn1 = gn_per_state(lo, hi, s2)
    lg(f"=== {tag} ===")
    # (4) eigenvalues
    lam = np.array([np.linalg.eigvalsh(Rp_const(c, s2)[2]) for c in range(lo, hi + 1)])
    lg(f"  eigenvalues of R: lambda_min from {lam[:,0].max():.3f} (c={lo}) down to {lam[:,0].min():.3f} (c={lo+int(np.argmin(lam[:,0]))}); lambda_max {lam[:,-1].min():.2f}-{lam[:,-1].max():.2f}; spread up to {np.max(lam[:,-1]/lam[:,0]):.0f}")
    # (3) pure-ramp constant K
    dc = 1
    ws = {c: Rp_const(c, s2)[0] for c in range(lo, hi + 1)}
    g = []
    for c in range(lo, hi + 1):
        a = ws[min(c + 1, hi)] - ws[max(c - 1, lo)]; a = a / (min(c + 1, hi) - max(c - 1, lo))
        R = Rp_const(c, s2)[2]; g.append(a @ np.linalg.solve(R, a))
    g = np.array(g); wts = np.ones(hi - lo + 1); wts[0] = wts[-1] = 0.5; wts /= wts.sum()
    # (1)+(2) scan
    def model_rho(mu, S):
        ne = 2 * (hi - lo) * S * max(1, round(152000 / (2 * (hi - lo) * S)))
        c = triangle_counter(NT + ne, NT, lo, hi, S); a = c * DA
        Jor = Jor_mean(lo, hi, s2, S, ne)
        el = (lag_excess(a, NT, NT + ne, mu, s2, w0, L, DELTA) - Jor) / Jor
        wq = np.bincount(c[NT:] - lo, minlength=hi - lo + 1) / ne
        eg = mu * float(sum(wq[i] * gn1[lo + i] for i in range(hi - lo + 1))) / Jor
        return el, eg, Jor
    xs = {}
    for p in (9.0, 10.0):
        mu = 2.0 ** -p; prev = None
        for S in range(int(0.05 / mu), int(0.25 / mu)):
            el, eg, Jor = model_rho(mu, S)
            rho = el / (plat - eg)
            if prev is not None and (prev[1] >= 0.5) != (rho >= 0.5):
                S0, r0 = prev; xs[p] = mu * (S0 + (0.5 - r0) / (rho - r0) * (S - S0)); break
            prev = (S, rho)
        lg(f"  continuous boundary at mu = 2^-{p:.0f}: x* = mu*S* = {xs.get(p, float('nan')):.4f}  (grid boundary S* = 28*2^(8-p): {28 * 2 ** (8 - p):.0f})")
    # collapse: eps_lag at fixed x for different mu
    coll = []
    for x in (0.05, 0.1, 0.2, 0.4):
        vals = []
        for p in (8.0, 9.0, 10.0):
            mu = 2.0 ** -p; S = int(round(x / mu)); el, eg, Jor = model_rho(mu, S); vals.append(el)
        coll.append((x, vals)); lg(f"  collapse: eps_lag at x = mu*S = {x}: " + ", ".join(f"mu=2^-{p:.0f}: {v:.4f}" for p, v in zip((8, 9, 10), vals)))
    # G(x) and local slope q(x) at mu = 2^-9 over a wide x range; pure-ramp comparison
    Gx = []
    for S in (3, 5, 7, 10, 14, 20, 28, 40, 56, 80, 112, 160, 224, 320, 500, 1000, 2000, 5000):
        mu = 2.0 ** -9; el, eg, Jor = model_rho(mu, S); K = float(wts @ g) / Jor
        Gx.append((mu * S, el, K / (mu * S) ** 2))
    Gx = np.array(Gx)
    q = -np.gradient(np.log(Gx[:, 1]), np.log(Gx[:, 0]))
    lg("  x = mu*S | eps_lag (model) | eps_lag steady pure ramp K/x^2 | ratio model/ramp | local slope q | q/(q+1)")
    for (x, el, er), qq in zip(Gx, q):
        lg(f"   {x:8.4f} | {el:9.4f} | {er:9.4f} | {el/er:6.3f} | {qq:5.2f} | {qq/(qq+1):.2f}")
    # number of adaptation time constants per half period at the measured optimum
    mo = [m for m in A["mu_opt"] if m["bracketed"] and m["rho_at_opt"] <= 0.75]
    ntc = [(m["S"], 76 * (hi - lo) / 76 * m["S"] * 2.0 ** m["log2mu_refined"] * lam[:, 0].min(), (hi - lo) * m["S"] * 2.0 ** m["log2mu_refined"] * np.median(lam[:, 0])) for m in mo]
    lg("  at the measured optimum: half period = (c_hi - c_lo)*S symbols; time constants per half period for the slowest mode (lambda_min at the harsh end / median lambda_min):")
    lg("   " + "  ".join(f"S={s}: {a:.1f}/{b:.1f}" for s, a, b in ntc))
    res[tag] = dict(xstar=xs, collapse=coll, Gx=Gx.tolist(), q=q.tolist(), lam_min=lam[:, 0].tolist(), lam_max=lam[:, -1].tolist(), ntc=ntc)
json.dump(res, open(f"{OUT}/explain.json", "w"), default=float)

# figures
M = {t: json.load(open(f"{OUT}/{t}.json")) for t in ("primary_16", "primary_14", "control_16", "control_14")}
S_ = json.load(open(f"{OUT}/mu_opt_summary.json"))
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
for t, col in (("primary_16", 'tab:blue'), ("control_16", 'tab:green'), ("primary_14", 'tab:orange'), ("control_14", 'tab:red')):
    b = M[t]["boundary"]; mus = sorted(float(k) for k in b)
    f = lambda v: np.nan if v in (None, "undef") else v
    axs[0].loglog(mus, [f(b[repr(m) if repr(m) in b else str(m)][0]) for m in mus], 'o', color=col, label=f"{t} measured")
    axs[0].loglog(mus, [f(b[repr(m) if repr(m) in b else str(m)][1]) for m in mus], '-', color=col, lw=1, label=f"{t} theory model")
    for var, st in (("theory", '-'), ("semi-empirical", '--')):
        pts = S_[f"{t}|{var}"]; used = pts["used"]
        sel = [p for p in pts["points"] if p["S"] in used]
        axs[1].loglog([1.0 / p["S"] for p in sel], [2.0 ** p["log2mu"] for p in sel], st, color=col, lw=1, label=f"{t} {var}" if t.endswith("16") else None)
    A = json.load(open(f"results/final/analysis_{t}.json")); mo = [m for m in A["mu_opt"] if m["S"] in S_[f"{t}|theory"]["used"]]
    axs[1].loglog([1.0 / m["S"] for m in mo], [2.0 ** m["log2mu_refined"] for m in mo], 'o', color=col, ms=4)
xx = np.geomspace(1e-3, 3, 50)
axs[0].loglog(2.0 ** -np.arange(5, 12, .5), 0.1095 / 2.0 ** -np.arange(5, 12, .5), 'k:', lw=1, label="S* = 0.1095 / mu")
axs[0].set_xlabel('mu'); axs[0].set_ylabel('S*_MSE (rho_th = 0.5)'); axs[0].legend(fontsize=6); axs[0].set_title('tracking boundary: measured (dots) vs theory model (lines)', fontsize=8)
axs[1].set_xlabel('variation rate 1/S'); axs[1].set_ylabel('optimum mu'); axs[1].legend(fontsize=6); axs[1].set_title('optimum step size: measured (dots) vs model', fontsize=8)
E = json.load(open(f"{OUT}/explain.json"))
for t, col in (("primary_16", 'tab:blue'), ("control_16", 'tab:green')):
    G = np.array(E[t]["Gx"]); axs[2].loglog(G[:, 0], G[:, 1], 'o-', color=col, label=f"{t}: mean-weight model")
    axs[2].loglog(G[:, 0], G[:, 2], ':', color=col, label=f"{t}: steady pure ramp K/x^2 (slope -2)")
axs[2].axhline(0.5 * 1.829, color='tab:blue', lw=.6, ls='--'); axs[2].axhline(0.5 * 0.976, color='tab:green', lw=.6, ls='--')
axs[2].set_xlabel('x = mu * S'); axs[2].set_ylabel('lag excess MSE / J_or'); axs[2].legend(fontsize=6); axs[2].set_title('lag depends on mu*S only; flatter than the ramp law', fontsize=8)
for a in axs: a.grid(alpha=.3, which='both')
fig.tight_layout(); fig.savefig(f"{OUT}/fig_model_boundary_exponent.png", dpi=150)
