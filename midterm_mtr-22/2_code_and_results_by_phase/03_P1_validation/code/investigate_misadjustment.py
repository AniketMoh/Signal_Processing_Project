"""Investigation of the 1.48x LMS misadjustment discrepancy (finding F-1).  Level L1, floating point.
The LMS loop (lms_lib.lms_receivers) is used UNCHANGED.  The original V4b test and its result are untouched:
this script only adds evidence and a separate reference test (V4d).  Run:  python3 investigate_misadjustment.py
"""
import json, numpy as np
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import CFG, DA, sigma_from_ebn0
from lms_lib import lms_receivers, delayed_symbols
from misadj_lib import *

LOG = {}
DELTA = 2                       # Dfix chosen in V5
SIG = sigma_from_ebn0(14.0); S2 = SIG ** 2
HCTRL = np.array([1.0, 77 * DA, 0.1])          # the V4 control channel (a = 0.6016)
N = 1_000_000; BURN = 100_000                  # steady-state window = last 900,000 symbols (as in V4)
SEEDS = list(range(1000, 1016))                # 16 independent pilot seeds


def ci(v):
    v = np.asarray(v, float); n = len(v)
    m = v.mean(); se = v.std(ddof=1) / np.sqrt(n)
    return m, stats.t.ppf(0.975, n - 1) * se


def one_run(h, mu_list, seed, gaussian=False, with_U=False):
    """One independent data record -> dict of paired measurements for every mu."""
    x, r = simulate_static(h, N, seed, SIG, gaussian)
    w, J, R = wiener(h, DELTA, S2)
    d = delayed_symbols(x, DELTA)
    e_o = d - np.convolve(r, w)[:N]            # fixed Wiener filter error (u[k] = r[n-k] -> plain FIR convolution)
    base = np.mean(e_o[BURN:] ** 2)            # same-data reference for the paired estimator
    out = dict(J=J, trR=np.trace(R), base=base, e_o=e_o, r=r, x=x, d=d, w=w, R=R, mu={})
    for mu in mu_list:
        e = run_lms(r, x, DELTA, mu)
        m = np.mean(e[BURN:] ** 2)
        out["mu"][mu] = dict(mse=m, ex_unpaired=m / J - 1, ex_paired=(m - base) / J)
    return out


# ------------------------------------------------------------ item 1: formula and its assumptions
def item1():
    print("\n[1] Formula used by V4b:  excess = q/(1-q),  q = mu*tr(R)/2,  tr(R) = L*(sum h^2 + sigma^2)   (normalised by J_min)")
    print("    Assumptions: (A1) small mu; (A2) u(n) independent of the weight error w(n)-w_o; (A3) the optimal-filter error e_o(n)")
    print("    is white (uncorrelated in time) and independent of u(n) (Haykin 'independence theory'); A3 gives gradient-noise")
    print("    covariance J_min*R.  q/(1-q) is the sum over eigenvalues mu*lam/(2-mu*lam) with lam replaced by its mean.")
    h = HCTRL; w, J, R = wiener(h, DELTA, S2); lam = np.linalg.eigvalsh(R)
    print(f"    This channel: J_min = {J:.5f}, tr(R) = {np.trace(R):.3f}, eigenvalues of R: min {lam.min():.3f}, max {lam.max():.3f}, cond {lam.max()/lam.min():.1f}")
    for k in (7, 8, 9, 10):
        mu = 2.0 ** -k
        q = mu * np.trace(R) / 2; M1 = q / (1 - q); M2 = np.sum(mu * lam / (2 - mu * lam))
        print(f"    mu=2^-{k}: trace form {100*M1:.3f}%  eigenvalue form {100*M2:.3f}%  (they differ by {100*(M2/M1-1):+.2f}%)")
    LOG["item1"] = dict(J_min=J, trR=float(np.trace(R)), eig_min=float(lam.min()), eig_max=float(lam.max()), cond=float(lam.max() / lam.min()))


# ------------------------------------------------------------ item 3: implementation audit
def item3():
    print("\n[3] Implementation audit")
    rng = np.random.default_rng(5); h = HCTRL; n = 4000
    x, r = simulate_static(h, n, 5, SIG); d = delayed_symbols(x, DELTA); mu = 2.0 ** -8
    # (a) plain-python reference LMS vs the project (numba) loop
    w = np.zeros(L); u = np.zeros(L); e_ref = np.zeros(n)
    for t in range(n):
        u = np.concatenate(([r[t]], u[:-1]))
        y = w @ u; e_ref[t] = d[t] - y; w = w + mu * e_ref[t] * u
    e_prj = run_lms(r, x, DELTA, mu)
    a = np.max(np.abs(e_ref - e_prj)); print(f"    (a) plain-python LMS vs project loop, {n} symbols: max |difference| = {a:.2e}")
    # (b) project loop vs row-based implementation
    xr, rr = simulate_static(h, 200_000, 6, SIG); U = input_matrix(rr); dd = delayed_symbols(xr, DELTA)
    b = np.max(np.abs(lms_rows(U, dd, mu) - run_lms(rr, xr, DELTA, mu))); print(f"    (b) row-based LMS vs project loop, 200000 symbols: max |difference| = {b:.2e}")
    # (c) alignment: d[n] must equal x[n-Delta]; Wiener error by convolution == by explicit rows
    ok_al = np.array_equal(d[DELTA:], x[:-DELTA]) and np.all(d[:DELTA] == 0)
    w_o, J, R = wiener(h, DELTA, S2)
    c = np.max(np.abs((dd - U @ w_o) - (dd - np.convolve(rr, w_o)[:len(rr)]))); print(f"    (c) d[n]=x[n-{DELTA}] exactly: {ok_al}; Wiener error via rows vs via convolution: max diff {c:.1e}")
    # (d) J_min by brute force: fixed Wiener filter on long data, 8 seeds
    base = [np.mean((delayed_symbols(*(lambda s: (s[0],))(simulate_static(h, N, s, SIG)), DELTA) - np.convolve(simulate_static(h, N, s, SIG)[1], w_o)[:N])[BURN:] ** 2) for s in SEEDS[:8]]
    m, hw = ci(base); print(f"    (d) measured MSE of the fixed Wiener filter: {m:.5f} +- {hw:.5f} (95%) vs theory J_min {J:.5f}  -> ratio {m/J:.4f}")
    # (e) wrong delay is clearly worse; error power is in units of symbol energy 1
    xx, rx = simulate_static(h, 200_000, 7, SIG)
    wr = [np.mean((delayed_symbols(xx, D) - np.convolve(rx, wiener(h, D, S2)[0])[:200_000])[5000:] ** 2) for D in (0, 2, 8, 17)]
    print(f"    (e) Wiener-filter MSE for Delta=0,2,8,17: {np.round(wr,4)}  (Delta=2 is in the flat minimum, J_min={J:.4f})")
    # (f) stationarity of the steady-state window: MSE in 9 consecutive blocks of 100k for mu=2^-8
    e = run_lms(*(lambda s: (s[1], s[0]))(simulate_static(h, N, 1000, SIG)), DELTA, mu)
    blocks = [np.mean(e[BURN + i * 100_000: BURN + (i + 1) * 100_000] ** 2) for i in range(9)]
    first, last = np.mean(blocks[:3]), np.mean(blocks[-3:])
    print(f"    (f) block MSEs (mu=2^-8, 1 seed): {np.round(blocks,5)}; first/last third = {first:.5f}/{last:.5f} (no trend beyond noise)")
    print(f"        convergence time at mu=2^-10 was ~4000 symbols (P1 learning curves); window starts at {BURN} = 25x that.")
    LOG["item3"] = dict(py_vs_project=float(a), rows_vs_project=float(b), alignment_ok=bool(ok_al), wiener_err_conv_vs_rows=float(c),
                        jmin_measured=m, jmin_theory=J, jmin_ratio=m / J, delta_mse=[float(v) for v in wr], blocks=[float(v) for v in blocks])
    return a < 1e-12 and b < 1e-12 and ok_al and abs(m / J - 1) < 0.01


# ------------------------------------------------------------ items 2, 4, 6, 7: the multi-seed table and mechanisms
def table_mu(h, label, gaussian=False, seeds=SEEDS, mus=(7, 8, 9, 10), do_numerics=True):
    w, J, R = wiener(h, DELTA, S2); trR = np.trace(R)
    mu_list = [2.0 ** -k for k in mus]
    runs = [one_run(h, mu_list, s, gaussian) for s in seeds]
    kx = 0.0 if gaussian else -2.0
    C = exact_C(h, w, DELTA, S2, kx=kx)
    rows = []
    # empirical C(j) and residual autocorrelation from the data (no adaptation involved)
    Ce = np.mean([gradient_noise_sums(q["e_o"], q["r"], kmax=20, skip=BURN) for q in runs], axis=0)
    acf = np.mean([[np.mean(q["e_o"][BURN + j:] * q["e_o"][BURN: len(q["e_o"]) - j]) / np.mean(q["e_o"][BURN:] ** 2) for j in range(0, 9)] for q in runs], axis=0)
    for mu in mu_list:
        un = [q["mu"][mu]["ex_unpaired"] for q in runs]; pa = [q["mu"][mu]["ex_paired"] for q in runs]
        qq = mu * trR / 2; tb = qq / (1 - qq); fo = first_order_excess(mu, C) / J
        mse = [q["mu"][mu]["mse"] for q in runs]
        row = dict(mu=mu, J_min=J, mse_meas=float(np.mean(mse)), mse_ci=float(ci(mse)[1]),
                   excess_abs_unpaired=float(np.mean(un) * J), excess_abs_paired=float(np.mean(pa) * J),
                   excess_rel_unpaired=float(ci(un)[0]), excess_rel_unpaired_ci=float(ci(un)[1]),
                   excess_rel_paired=float(ci(pa)[0]), excess_rel_paired_ci=float(ci(pa)[1]),
                   textbook=tb, firstorder_exact=fo,
                   ratio_textbook_unpaired=float(ci(un)[0] / tb), ratio_textbook_paired=float(ci(pa)[0] / tb),
                   ratio_textbook_paired_ci=float(ci(pa)[1] / tb), ratio_exact_paired=float(ci(pa)[0] / fo), ratio_exact_paired_ci=float(ci(pa)[1] / fo))
        rows.append(row)
    print(f"\n   --- {label}: h = {np.round(h,4)}, J_min = {J:.5f}, tr(R) = {trR:.3f}, {len(seeds)} seeds x {N} symbols (window {N-BURN}) ---")
    print("   mu      J_min    MSE_meas(+-95%)      excess_meas(abs)  excess_textbook(abs)  excess_exact1st(abs)  | meas/textbook (unpaired | paired +-95%)  meas/exact1st (paired +-95%)")
    for r_ in rows:
        print(f"   2^-{int(-np.log2(r_['mu']))}   {J:.5f}  {r_['mse_meas']:.5f}+-{r_['mse_ci']:.5f}   {r_['excess_abs_paired']:.3e}       {r_['textbook']*J:.3e}         {r_['firstorder_exact']*J:.3e}      |  {r_['ratio_textbook_unpaired']:.3f} | {r_['ratio_textbook_paired']:.3f} +-{r_['ratio_textbook_paired_ci']:.3f}      {r_['ratio_exact_paired']:.3f} +-{r_['ratio_exact_paired_ci']:.3f}")
    print(f"   C(0): exact {C[0]:.4f}, data {Ce[0]:.4f}, J*trR {J*trR:.4f};  C(1): exact {C[1]:.4f}, data {Ce[1]:.4f};  sum_(j>=1) C: exact {C[1:].sum():.4f}, data(<=20) {Ce[1:].sum():.4f}")
    print(f"   residual-error autocorrelation lag 1..4 (data): {np.round(acf[1:5],4)}   (white would be 0 +- {1.96/np.sqrt(len(seeds)*(N-BURN)):.4f})")
    res = dict(rows=rows, C_exact=C[:12].tolist(), C_data=Ce[:12].tolist(), acf=acf.tolist(), J=J, trR=float(trR))
    if do_numerics:
        res["numerics"] = numeric_controls(h, runs[:8], mu_list, J, trR)
    return res, runs


def numeric_controls(h, runs, mu_list, J, trR):
    """Independent numerical references on 8 of the records:
       lin  : first-order LMS model that keeps the TRUE correlated data but replaces u u^T by R in the update
       shuf : the same LMS (lms_rows) on time-shuffled rows (u,d) -> independence assumption true by construction
       unshuf: lms_rows on unshuffled rows (check)"""
    out = {}
    print("   numerical controls (8 records), paired excess / textbook:")
    for mu in mu_list:
        lin, shuf, unsh = [], [], []
        tb = (mu * trR / 2) / (1 - mu * trR / 2)
        for k, q in enumerate(runs):
            U = input_matrix(q["r"]); d = q["d"]; e_o = q["e_o"]; R = q["R"]
            lin.append((linearised_mse(U, e_o, R, mu, BURN) - np.mean(e_o[BURN:] ** 2)) / J)
            perm = np.random.default_rng(900 + k).permutation(len(d))
            es = lms_rows(np.ascontiguousarray(U[perm]), d[perm], mu); eos = e_o[perm]
            shuf.append((np.mean(es[BURN:] ** 2) - np.mean(eos[BURN:] ** 2)) / J)
        out[str(mu)] = dict(lin=ci(lin)[0] / tb, lin_ci=ci(lin)[1] / tb, shuf=ci(shuf)[0] / tb, shuf_ci=ci(shuf)[1] / tb)
        print(f"     mu=2^-{int(-np.log2(mu))}: linearised model {out[str(mu)]['lin']:.3f} +-{out[str(mu)]['lin_ci']:.3f};  time-shuffled data {out[str(mu)]['shuf']:.3f} +-{out[str(mu)]['shuf_ci']:.3f}")
    return out


# ------------------------------------------------------------ item 5: ISI-strength sweep
def sweep():
    print("\n[5] ISI-strength sweep: h = s*[0, 0.6016, 0.1] added to a unit main tap (s = 0 is a flat channel), mu = 2^-9, 6 seeds x 1e6")
    print("    s     a      h2     cond(R)  lag-1 acf of e_o   meas/textbook (paired +-95%)   exact-model/textbook   meas/exact-model")
    mu = 2.0 ** -9; out = []
    for s in [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.25, 1.5]:
        h = np.array([1.0, s * HCTRL[1], s * HCTRL[2]])
        w, J, R = wiener(h, DELTA, S2); trR = np.trace(R)
        runs = [one_run(h, [mu], sd) for sd in SEEDS[:6]]
        pa = [q["mu"][mu]["ex_paired"] for q in runs]
        tb = (mu * trR / 2) / (1 - mu * trR / 2)
        C = exact_C(h, w, DELTA, S2); fo = first_order_excess(mu, C) / J
        acf1 = np.mean([np.mean(q["e_o"][BURN + 1:] * q["e_o"][BURN:-1]) / np.mean(q["e_o"][BURN:] ** 2) for q in runs])
        lam = np.linalg.eigvalsh(R)
        m, hw = ci(pa)
        rec = dict(s=s, a=h[1], h2=h[2], cond=float(lam.max() / lam.min()), acf1=float(acf1), meas_over_tb=m / tb, meas_over_tb_ci=hw / tb,
                   exact_over_tb=fo / tb, meas_over_exact=m / fo, meas_over_exact_ci=hw / fo, J=J)
        out.append(rec)
        print(f"    {s:4.2f}  {h[1]:.4f} {h[2]:.4f}  {rec['cond']:6.2f}   {acf1:+.4f}          {rec['meas_over_tb']:.3f} +-{rec['meas_over_tb_ci']:.3f}              {rec['exact_over_tb']:.3f}                 {rec['meas_over_exact']:.3f} +-{rec['meas_over_exact_ci']:.3f}")
    return out


def figures(tabs, sw):
    res, _ = tabs
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    s_ = [r["s"] for r in sw]
    ax[0].errorbar(s_, [r["meas_over_tb"] for r in sw], yerr=[r["meas_over_tb_ci"] for r in sw], fmt="o-", label="measured / textbook (paired, 95% CI)")
    ax[0].plot(s_, [r["exact_over_tb"] for r in sw], "s--", label="exact correlated-error model / textbook")
    ax[0].axhline(1, color="k", lw=.8); ax[0].axhline(1.2, color="r", ls=":", lw=.8, label="20% tolerance"); ax[0].axhline(.8, color="r", ls=":", lw=.8)
    ax[0].set_xlabel("ISI strength s  (s=0 flat, s=1 the V4 control channel)"); ax[0].set_ylabel("excess MSE ratio"); ax[0].set_title("Ratio grows as ISI is added"); ax[0].legend(fontsize=7)
    j = np.arange(0, 9)
    ax[1].bar(j - 0.2, res["C_exact"][:9], 0.4, label="exact (algebra)"); ax[1].bar(j + 0.2, res["C_data"][:9], 0.4, label="from data")
    ax[1].set_xlabel("lag j"); ax[1].set_ylabel("C(j) = E[e_o(n)e_o(n-j) u(n)ᵀu(n-j)]"); ax[1].set_title("Gradient-noise correlation (control channel)"); ax[1].legend(fontsize=8)
    ax[2].bar(j, res["acf"][:9], color="C2"); ax[2].set_xlabel("lag j"); ax[2].set_ylabel("autocorrelation of e_o"); ax[2].set_title("Residual error of the Wiener filter is not white")
    fig.tight_layout(); fig.savefig("results/fig_M1_misadjustment_investigation.png", dpi=130); plt.close(fig)


def main():
    item1()
    ok3 = item3()
    print("\n[2,4,6,7] Per-mu table, control channel (a = 0.6016, 14 dB, Delta = 2), binary BPSK data")
    tabs = table_mu(HCTRL, "binary data, ISI channel")
    print("\n   Eigenvalues of R (control channel):", np.round(np.linalg.eigvalsh(tabs[0] and wiener(HCTRL, DELTA, S2)[2]), 3))
    R = wiener(HCTRL, DELTA, S2)[2]
    print("   R first row (autocorrelation of the received signal at lags 0..5):", np.round(R[0, :6], 4), " (white input would be [sigma^2+sum h^2, 0, 0, ...])")
    print("\n   Controls on the same table:")
    gaus = table_mu(HCTRL, "GAUSSIAN data, ISI channel", gaussian=True, seeds=SEEDS[:8], mus=(8, 9, 10), do_numerics=False)
    flat = table_mu(np.array([1.0, 0, 0]), "FLAT channel, binary data", seeds=SEEDS[:8], mus=(8, 9, 10), do_numerics=False)
    sw = sweep()
    figures(tabs, sw)
    # ---------------- V4d: separate, validated reference test (does NOT replace V4b)
    rows = tabs[0]["rows"][1:]                                     # mu = 2^-8, 2^-9, 2^-10 (the V4b set)
    okd = all(abs(r["ratio_exact_paired"] - 1) < 0.20 for r in rows)
    okd2 = all(abs(r["ratio_exact_paired"] - 1) < 2 * r["ratio_exact_paired_ci"] + 0.05 for r in rows)
    print("\n=== RESULTS ===")
    print(f"audit passes: {ok3}")
    print(f"V4b (original, textbook, 20% criterion)  [kept]: ratios meas/textbook = {[round(r['ratio_textbook_paired'],3) for r in rows]} -> FAIL stays")
    print(f"V4d (reference: exact first-order correlated-error model, same 20% criterion): ratios = {[round(r['ratio_exact_paired'],3) for r in rows]} -> {'PASS' if okd else 'FAIL'}")
    LOG.update(table=tabs[0], gaussian=gaus[0], flat=flat[0], sweep=sw, V4d=dict(passed=bool(okd), within_2se=bool(okd2), ratios=[r["ratio_exact_paired"] for r in rows]))
    json.dump(LOG, open("results/misadjustment_investigation.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
