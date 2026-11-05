"""P2 FINAL (FREEZE-1, approved 20 Oct): abrupt channel transition, level L1, FINAL seeds 2000-2099, supervised LMS, Delta = 2, L = 16,
N_T = 120000 (owner decision 20 Oct, 23:40 IST; supersedes E-6 N_T = 60000 for P2, whose results are preserved).  Copy of p2_abrupt.py (the pilot script, kept unchanged); only the configuration differs.
usage: python3 p2_final.py <EbN0_dB>
Results 5 (MSE vs time), 6 (reacquisition vs mu), 7 (coefficient trajectories) and BER vs time (R1/R2/R3).
Predictions (mean-weight transient model, analytic frozen-filter MSE, first-order static excess) are computed from the
channel alone and compared with measurements; nothing is fitted.  The LMS loop is lms_lib.lms_receivers, unchanged.
Run:  python3 p2_final_NT120k.py 16 > results/p2_final_NT120k_16dB_console_log.txt
"""
import json, sys, time, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from exp_lib import *

EB = float(sys.argv[1]); S2 = sigma_from_ebn0(EB) ** 2
N_T, N_PRE, N_POST = 120000, 20000, 100000
N_C = N_T + N_PRE; N_TOT = N_C + N_POST
MUS = [2.0 ** -k for k in (7, 8, 9, 10)]
STEPS = {"large_up (c 40->116, a 0.31->0.91)": (40, 116), "mid_up (c 40->77, a 0.31->0.60)": (40, 77), "down (c 116->40, a 0.91->0.31)": (116, 40)}
SEEDS = list(range(2000, 2100))
KAPPA, W = 0.25, 64                      # provisional (D-09), fixed at FREEZE-1
STRIDE = 16                              # coefficient history stride
BLK = 500                                # BER block length
PRE_WIN = 2000                           # samples kept before N_C for the bootstrap series
LOG = {}


def moving_avg(a, w):
    cs = np.cumsum(np.insert(a, 0, 0.0), axis=-1)
    return (cs[..., w:] - cs[..., :-w]) / w                      # ma[i] = mean(a[i : i+w])  (trailing window ending at i+w-1)


def n_rec_from(mean_series, thr):
    """mean_series: seed-mean e^2 for n = N_C - (W-1) ... N_TOT-1 (so the first MA value is the window ending at N_C)."""
    ma = moving_avg(mean_series, W)                                # ma[k] = MA ending at n = N_C + k
    bad = ma > thr
    if bad.ndim == 1:
        if not bad.any(): return 0
        last = np.nonzero(bad)[0][-1]
        return float(last + 1) if last < len(ma) - 1 else float("nan")
    out = np.full(bad.shape[0], np.nan)
    for i in range(bad.shape[0]):
        out[i] = n_rec_from(mean_series[i], thr)
    return out


def static_reference(cs):
    """J_ss(c, mu): steady-state a-priori MSE of LMS on a STATIC channel (D-09 reference), 20 seeds x 300000 (last 200000)."""
    ref = {}
    for c in cs:
        w, Jmin, R, p = Rp_const(c, S2)
        cc = np.full(300000, c, dtype=np.int64)
        for mu in MUS:
            v = []
            for seed in SEEDS[:20]:
                ex = make_exp_from_counter(cc, N_T, EB, seed)
                _, _, eA, _, _ = run_lms(ex, mu, 10 ** 9)
                v.append(np.mean(eA[-200000:] ** 2))
            ref[(c, mu)] = (float(np.mean(v)), float(np.std(v, ddof=1) / np.sqrt(len(v))), Jmin)
    return ref


def main():
    t0 = time.time()
    cs_all = sorted({c for ab in STEPS.values() for c in ab})
    print(f"P2 abrupt transition. N_T={N_T}, N_pre={N_PRE}, N_post={N_POST}, N_C={N_C}; {len(SEEDS)} FINAL seeds; Eb/N0={EB} dB; L={L}, Delta={DELTA}; kappa={KAPPA}, W={W}")
    ref = static_reference(cs_all)
    print("\nStatic reference levels (20 seeds x 200000 symbols):  c  mu  J_min  J_ss(+-SE)  eps_static(%)  first-order exact eps(%)")
    for (c, mu), (j, se, jm) in ref.items():
        h = np.array([1.0, c * DA, H2]); w, J, R = wiener(h, DELTA, S2); C = exact_C(h, w, DELTA, S2)
        print(f"   c={c:3d} mu=2^-{int(-np.log2(mu))}: J_min {jm:.5f}  J_ss {j:.5f}+-{se:.5f}  eps_static {100*(j/jm-1):6.2f}  first-order {100*first_order_excess(mu, C)/J:6.2f}")
    LOG["static_reference"] = {f"{c}_{mu}": dict(J_ss=v[0], se=v[1], J_min=v[2]) for (c, mu), v in ref.items()}
    out_all = {}
    fig1, ax1 = plt.subplots(1, 3, figsize=(17, 4.6)); fig3, ax3 = plt.subplots(1, 3, figsize=(17, 4.2))
    fig4, ax4 = plt.subplots(1, 3, figsize=(17, 4.2)); fig5, ax5 = plt.subplots(1, 2, figsize=(11, 4.2))
    for si, (sname, (cA, cB)) in enumerate(STEPS.items()):
        wA, JA, RA, pA = Rp_const(cA, S2); wB, JB, RB, pB = Rp_const(cB, S2)
        lamB, QB = np.linalg.eigh(RB); v0 = wA - wB
        coef0 = QB.T @ v0
        J_frozen = 1 - 2 * wA @ pB + wA @ RB @ wA              # analytic MSE of the filter trained on A, used on B
        print(f"\n=== step {sname} ===  J_min(A) {JA:.5f}  J_min(B) {JB:.5f}  analytic frozen-filter MSE on B {J_frozen:.4f} (excess {100*(J_frozen/JB-1):.0f} % over oracle); lambda_min(R_B) {lamB[0]:.3f}")
        c_arr = step_counter(cA, cB, N_T, N_PRE, N_POST)
        acc = {mu: dict(e3=np.zeros(N_TOT), e2=np.zeros(N_TOT), E3=np.zeros((len(SEEDS), N_POST + W - 1), np.float32),
                        b1=np.zeros(N_TOT, np.int32), b2=np.zeros(N_TOT, np.int32), b3=np.zeros(N_TOT, np.int32),
                        wH=np.zeros((N_TOT // STRIDE + 1, L))) for mu in MUS}
        for k, seed in enumerate(SEEDS):
            ex = make_exp_from_counter(c_arr, N_T, EB, seed)
            for mu in MUS:
                yA, yF, eA, eF, wH = run_lms(ex, mu, STRIDE)
                a = acc[mu]
                a["e3"] += eA ** 2; a["e2"] += eF ** 2
                a["E3"][k] = (eA[N_C - (W - 1):] ** 2)
                i1, i2, i3 = ber_indicators(ex, yA, yF)
                a["b1"] += i1; a["b2"] += i2; a["b3"] += i3
                a["wH"] += wH[: a["wH"].shape[0]] if wH.shape[0] >= a["wH"].shape[0] else np.vstack([wH, np.zeros((a["wH"].shape[0] - wH.shape[0], L))])
        res = {}
        rng = np.random.default_rng(7); Bn = 200
        boot_idx = rng.integers(0, len(SEEDS), (Bn, len(SEEDS)))
        print("   mu     J_pre   J_ss(B)ref  eps_stat(B)%   R2 post MSE (meas | analytic)   R3 first-64 MSE   N_rec meas [95% boot]     N_rec predicted   tau_slow  train-conv  area(meas/model)")
        for mu in MUS:
            a = acc[mu]; ns = len(SEEDS)
            m3 = a["e3"] / ns; m2 = a["e2"] / ns
            J_pre = float(np.mean(m3[N_C - 10000:N_C]))
            Jss_B, se_B, _ = ref[(cB, mu)]
            Jss_A = ref[(cA, mu)][0]
            r2_post = float(np.mean(m2[N_C + L + M: N_TOT]))
            r3_first = float(np.mean(m3[N_C + L + M: N_C + L + M + 64]))
            thr = (1 + KAPPA) * Jss_B
            series = a["E3"].astype(np.float64).mean(axis=0)
            nrec = n_rec_from(series, thr)
            nb = np.array([n_rec_from(a["E3"][ix].astype(np.float64).mean(axis=0), thr) for ix in boot_idx])
            lo, hi = (np.nanpercentile(nb, 2.5), np.nanpercentile(nb, 97.5)) if np.isfinite(nb).sum() > 0.9 * Bn else (float("nan"), float("nan"))
            # prediction: mean-weight transient on top of the first-order static level
            h = np.array([1.0, cB * DA, H2]); wl, Jl, _ = wiener(h, DELTA, S2); C = exact_C(h, wl, DELTA, S2)
            Jss_pred = JB + first_order_excess(mu, C)
            kk = np.arange(0, N_POST)
            trans = (lamB[:, None] * (coef0[:, None] ** 2) * (1 - mu * lamB[:, None]) ** (2 * kk[None, :])).sum(axis=0)
            Jpred = Jss_pred + trans
            badp = np.nonzero(Jpred > thr)[0]
            nrec_pred = float(badp[-1] + 1 + (L - 1)) if len(badp) else float(L - 1)     # k counted from N_C (window fills after L-1)
            tau = 1.0 / (2 * mu * lamB[0])
            kmin = N_C + L - 1
            area_meas = float(np.sum(m3[kmin:] - Jss_B)); area_pred = float(np.sum(trans[: N_TOT - kmin]))
            area_ratio = area_meas / area_pred
            # training convergence at the start state (A): 500-MA of the seed-mean within 10 % of static reference, staying
            ma = moving_avg(m3[:N_T], 500); badc = np.nonzero(ma > 1.10 * Jss_A)[0]
            n_conv = int(badc[-1] + 1 + 499) if len(badc) else 499
            res[mu] = dict(J_pre=J_pre, Jss_A=Jss_A, Jss_B=Jss_B, eps_static_B=Jss_B / JB - 1, R2_post=r2_post, R2_post_analytic=float(J_frozen),
                           R3_first64=r3_first, N_rec=nrec, N_rec_lo=float(lo), N_rec_hi=float(hi), N_rec_pred=nrec_pred, tau_slow=tau, n_conv_train=n_conv,
                           J_pre_over_ref=J_pre / Jss_A, area_ratio=area_ratio)
            print(f"   2^-{int(-np.log2(mu)):2d}  {J_pre:.5f}  {Jss_B:.5f}    {100*(Jss_B/JB-1):6.2f}      {r2_post:.4f} | {J_frozen:.4f}            {r3_first:.4f}        {nrec:7.0f} [{lo:6.0f},{hi:6.0f}]        {nrec_pred:7.0f}            {tau:9.0f}   {n_conv:6d}    {area_ratio:.3f}")
            # ---- figures
            tt = np.arange(N_TOT)
            sl = slice(N_C - 3000, N_C + 40000)
            blk = 64
            def blocks(v): 
                n_ = (len(v) // blk) * blk
                return v[:n_].reshape(-1, blk).mean(axis=1)
            x_ = (tt[sl][: (len(tt[sl]) // blk) * blk].reshape(-1, blk).mean(axis=1)) - N_C
            ax1[si].semilogy(x_, blocks(m3[sl]), label=f"R3 mu=2^-{int(-np.log2(mu))}", lw=1)
            ax1[si].semilogy(np.arange(N_POST)[:40000] + L - 1, Jpred[:40000], "k:", lw=.7)
            if mu == MUS[1]:
                ax1[si].semilogy(x_, blocks(m2[sl]), "k", lw=1.2, label="R2 (frozen) mu=2^-8")
        ax1[si].axhline(JB, color="gray", ls="--", lw=.8, label="oracle J_min(B)"); ax1[si].axhline(JA, color="gray", ls="-.", lw=.8, label="oracle J_min(A)")
        ax1[si].set_title(sname, fontsize=9); ax1[si].set_xlabel("n - N_C (symbols)"); ax1[si].set_ylabel("MSE (mean of 100 seeds, 64-symbol blocks)"); ax1[si].legend(fontsize=6)
        mus_a = np.array(MUS)
        ax3[si].errorbar(mus_a, [res[m]["N_rec"] for m in MUS], yerr=[[max(res[m]["N_rec"] - res[m]["N_rec_lo"], 0) if np.isfinite(res[m]["N_rec_lo"]) else 0 for m in MUS], [max(res[m]["N_rec_hi"] - res[m]["N_rec"], 0) if np.isfinite(res[m]["N_rec_hi"]) else 0 for m in MUS]], fmt="o-", label="measured (95% bootstrap)")
        ax3[si].plot(mus_a, [res[m]["N_rec_pred"] for m in MUS], "s--", label="mean-weight model")
        ax3[si].set_xscale("log", base=2); ax3[si].set_yscale("log"); ax3[si].set_xlabel("mu"); ax3[si].set_ylabel("N_rec (symbols)"); ax3[si].set_title(sname, fontsize=9); ax3[si].legend(fontsize=7)
        # coefficient trajectories at mu = 2^-8
        mu = MUS[1]; wm = acc[mu]["wH"] / len(SEEDS); tw = np.arange(wm.shape[0]) * STRIDE
        sl2 = (tw > N_C - 2000) & (tw < N_C + 30000)
        kk = (tw[sl2] - (N_C + L - 1)).clip(min=0)
        for i in range(5):
            line, = ax4[si].plot(tw[sl2] - N_C, wm[sl2, i], lw=1, label=f"w[{i}]")
            th = wB[i] + sum(QB[i, q] * coef0[q] * (1 - mu * lamB[q]) ** kk for q in range(L))
            ax4[si].plot(tw[sl2] - N_C, th, "k:", lw=.8)
            ax4[si].axhline(wB[i], color=line.get_color(), ls="--", lw=.5)
        ax4[si].set_title(sname + "  (mu=2^-8; dotted = mean-weight model, dashed = w_B*)", fontsize=8); ax4[si].set_xlabel("n - N_C"); ax4[si].set_ylabel("mean coefficient"); ax4[si].legend(fontsize=6, ncol=2)
        # BER vs time, mu = 2^-8
        a = acc[mu]; nb_ = (N_TOT // BLK) * BLK; ns = len(SEEDS)
        tb = np.arange(nb_ // BLK) * BLK + BLK / 2 - N_C
        for key, nm, col in (("b1", "R1 direct", "C3"), ("b2", "R2 frozen", "C3"), ("b3", "R3 adaptive", "C0")):
            pass
        for key, nm in (("b1", "R1 direct"), ("b2", "R2 frozen"), ("b3", "R3 adaptive")):
            ber = a[key][:nb_].reshape(-1, BLK).sum(axis=1) / (BLK * ns)
            sel = (tb > -3000) & (tb < 15000)
            ax5[0 if si == 0 else 1].semilogy(tb[sel], np.maximum(ber[sel], 1e-6), label=nm, lw=1) if si < 2 else None
        out_all[sname] = res
        if si < 2:
            ax5[si].set_title(sname + ", mu = 2^-8 (BER floor of the plot 1e-6)", fontsize=8); ax5[si].set_xlabel("n - N_C"); ax5[si].set_ylabel("BER (500-symbol blocks, 100 seeds)"); ax5[si].legend(fontsize=7)
        # BER summary
        a = acc[MUS[1]]
        def ber_win(key, s, e): return a[key][s:e].sum() / ((e - s) * len(SEEDS))
        LOG.setdefault("ber_summary", {})[sname] = dict(
            pre=dict(R1=ber_win("b1", N_C - 10000, N_C), R2=ber_win("b2", N_C - 10000, N_C), R3=ber_win("b3", N_C - 10000, N_C)),
            first2000_after=dict(R1=ber_win("b1", N_C + 16, N_C + 2016), R2=ber_win("b2", N_C + 16, N_C + 2016), R3=ber_win("b3", N_C + 16, N_C + 2016)),
            last20000=dict(R1=ber_win("b1", N_TOT - 20000, N_TOT), R2=ber_win("b2", N_TOT - 20000, N_TOT), R3=ber_win("b3", N_TOT - 20000, N_TOT)),
            bits_pre=10000 * len(SEEDS), bits_first=2000 * len(SEEDS), bits_last=20000 * len(SEEDS))
        print("   BER (mu=2^-8, 100 seeds):", {k: {r: f"{v:.2e}" for r, v in d.items()} for k, d in LOG["ber_summary"][sname].items() if isinstance(d, dict)})
        # mean MSE series kept (64-blocks, whole run) for the record
        LOG.setdefault("mse_series64", {})[sname] = {f"{mu}": dict(R3=[float(v) for v in (acc[mu]["e3"] / len(SEEDS))[: (N_TOT // 64) * 64].reshape(-1, 64).mean(axis=1)],
                                                              R2=[float(v) for v in (acc[mu]["e2"] / len(SEEDS))[: (N_TOT // 64) * 64].reshape(-1, 64).mean(axis=1)]) for mu in MUS}
        del acc
    # log-log slope of N_rec versus mu
    print("\nSlope of log N_rec vs log mu (least squares over the 4 mu; expectation from the mean-weight model: close to -1):")
    LOG["slopes"] = {}
    for sname, res in out_all.items():
        x = np.log([m for m in MUS]); y = np.log([res[m]["N_rec"] for m in MUS]); yp = np.log([res[m]["N_rec_pred"] for m in MUS])
        sl_m = np.polyfit(x, y, 1)[0]; sl_p = np.polyfit(x, yp, 1)[0]
        LOG["slopes"][sname] = dict(measured=float(sl_m), model=float(sl_p))
        print(f"   {sname}: measured {sl_m:.2f}, model {sl_p:.2f}")
    for f_, nm, ax_ in ((fig1, "fig_P2_mse_vs_time.png", None), (fig3, "fig_P2_nrec_vs_mu.png", None), (fig4, "fig_P2_coefficients.png", None), (fig5, "fig_P2_ber_vs_time.png", None)):
        f_.tight_layout(); f_.savefig(f"results/final_NT120k_{int(EB)}dB_" + nm, dpi=120)
    LOG["steps"] = {k: {f"{mu}": v for mu, v in r.items()} for k, r in out_all.items()}
    LOG["params"] = dict(N_T=N_T, N_PRE=N_PRE, N_POST=N_POST, seeds=[SEEDS[0], SEEDS[-1]], EB=EB, kappa=KAPPA, W=W, Delta=DELTA, L=L)
    json.dump(LOG, open(f"results/p2_final_NT120k_{int(EB)}dB_results.json", "w"), indent=1, default=float)
    print(f"\nDone in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main()
