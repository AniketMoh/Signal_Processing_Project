"""P6a predeclared tests (level L2, bit-true fixed point; fxp_lib.py).  usage: python3 p6a_tests.py T1|T2|T3|T4|T5|T6
Baseline word lengths (owner, 20 Oct): B_mul = 12, B_acc = 26; grid B_mul in {8, 12, 16}, B_acc in {16, 26, 32}; round to nearest
(truncation as sensitivity).  mu = 2^-p (powers of two, FPGA set).  L = 16, Delta = 2, N_T = 30000, supervised, same LMS equations.
All outputs go to results/p6a/ and are labelled L2.  L1 numbers quoted for comparison come from lms_lib (floating point) on the same data."""
import sys, os, json, time, numpy as np
from math import comb, factorial
from fractions import Fraction
from scipy.stats import norm
from exp_lib import *
from lms_lib import triangle_counter
from lms_lib import lms_receivers
from fxp_lib import fxp_receivers, quantize_signal, lfsr_noise, LFSR_TAPS, _lfsr_noise
from sweep import n_eval_for
OUT = "results/p6a"; os.makedirs(OUT, exist_ok=True)
NT = 30000; BM0, BA0 = 12, 26
lines = []
def lg(s): print(s, flush=True); lines.append(s)


def build(c, snr, seed, noise="gauss"):
    """Float channel + noise (L1 data path), then the L2 quantisation of r and d."""
    ex = make_exp_from_counter(c, NT, snr, seed)
    if noise == "lfsr":
        x = ex["x"]; ex["r"] = apply_channel(x, ex["taps"]) + lfsr_noise(len(x), ex["sigma"], seed + 500000)
    d = delayed_symbols(ex["x"], DELTA)
    return ex, quantize_signal(ex["r"]), quantize_signal(d)


def run_fx(ex, rq, dq, p, bm, ba, rnd=1, stride=10 ** 9):
    yA, yF, eA, eF, wH, st, up = fxp_receivers(rq, dq, L, p, NT, bm, ba, rnd, stride)
    return yA / 4096.0, yF / 4096.0, eA / 4096.0, eF / 4096.0, wH, st, up


def T1():
    """Equivalence: very wide words must reproduce L1."""
    lg("T1 equivalence: B_mul = 24, B_acc = 48, round to nearest, Gaussian noise, 14 dB, 5 seeds (5600-5604).  Criterion: |J_L2 - J_L1| < 1e-6.")
    ok = True
    for nm, c in (("static c=40", np.full(NT + 100000, 40)), ("triangle S=20", triangle_counter(NT + n_eval_for(20, 40, 116), NT, 40, 116, 20))):
        for p in (6, 8, 10):
            dj, dis, dw = [], 0, 0.0
            for sd in range(5600, 5605):
                ex, rq, dq = build(c, 14.0, sd)
                yA1, yF1, eA1, eF1, wH1 = run_lms(ex, 2.0 ** -p, 1000)
                yA2, yF2, eA2, eF2, wH2, _, _ = run_fx(ex, rq, dq, p, 24, 48, 1, 1000)
                dj.append(np.mean(eA2[NT:] ** 2) - np.mean(eA1[NT:] ** 2))
                dis += int(np.sum((yA1[NT:] >= 0) != (yA2[NT:] >= 0))); dw = max(dw, np.abs(wH1 - wH2).max())
            m = max(abs(v) for v in dj); ok &= m < 1e-6
            lg(f"   {nm:14s} mu=2^-{p:2d}: max |J_L2 - J_L1| = {m:.2e}   decision differences {dis} of {5*(len(c)-NT)}   max |w_L2 - w_L1| {dw:.2e}")
    lg(f"   T1 {'PASS' if ok else 'FAIL'}")


def T2():
    """Static convergence for every (B_mul, B_acc): excess MSE of L2 over L1 on the same data."""
    lg("T2 static convergence (14 dB, 6 seeds 5610-5615, 100000 evaluation symbols; entries = J_L2 / J_L1 - 1 in %, R3 steady state)")
    res = {}
    for c0 in (40, 116):
        c = np.full(NT + 100000, c0)
        data = [build(c, 14.0, sd) for sd in range(5610, 5616)]
        l1 = {p: np.mean([np.mean(run_lms(ex, 2.0 ** -p, 10 ** 9)[2][NT:] ** 2) for ex, _, _ in data]) for p in range(5, 12)}
        Jmin = Rp_const(c0, sigma_from_ebn0(14.0) ** 2)[1]
        lg(f"  c = {c0}: J_min {Jmin:.5f};  L1 excess over J_min (%): " + " ".join(f"2^-{p}:{100*(l1[p]/Jmin-1):.2f}" for p in range(5, 12)))
        lg("    (B_mul,B_acc) " + " ".join(f"   2^-{p:<3d}" for p in range(5, 12)))
        for bm in (8, 12, 16):
            for ba in (16, 26, 32):
                row = []
                for p in range(5, 12):
                    j = np.mean([np.mean(run_fx(ex, rq, dq, p, bm, ba)[2][NT:] ** 2) for ex, rq, dq in data])
                    row.append(100 * (j / l1[p] - 1)); res[f"{c0}|{bm}|{ba}|{p}"] = row[-1]
                lg(f"    ({bm:2d},{ba:2d})      " + " ".join(f"{v:8.2f}" for v in row))
    json.dump(res, open(f"{OUT}/T2.json", "w"))


def T3():
    """Update underflow: measured fraction of stalled updates vs the prediction from the L1 distribution of |mu e u|."""
    lg("T3 update underflow (B_mul = 12; static c = 116, 14 dB, 4 seeds 5620-5623).  Stall = nonzero exact update rounded to 0.")
    lg("   prediction (round to nearest): P(|mu*e*u| < LSB/2);  (truncation): P(0 <= mu*e*u < LSB)  -- from L1 e and u on the same data")
    c = np.full(NT + 60000, 116); data = [build(c, 14.0, sd) for sd in range(5620, 5624)]
    res = {}
    for ba in (16, 26, 32):
        lsb = 2.0 ** -(ba - 2)
        for p in range(5, 12):
            mu = 2.0 ** -p
            prod = []
            for ex, rq, dq in data:
                eA1 = run_lms(ex, mu, 10 ** 9)[2][NT:]; r = ex["r"]
                U = np.stack([r[NT - k: len(r) - k] for k in range(L)], axis=1)
                prod.append((mu * eA1[:, None] * U).ravel())
            prod = np.concatenate(prod)
            pred_n = float(np.mean(np.abs(prod) < lsb / 2)); pred_t = float(np.mean((prod >= 0) & (prod < lsb)))
            out = []
            for rnd in (1, 0):
                st = up = 0; J2 = []; J1 = []
                for ex, rq, dq in data:
                    yA, yF, eA, eF, wH, s_, u_ = run_fx(ex, rq, dq, p, 12, ba, rnd)
                    st += s_; up += u_; J2.append(np.mean(eA[NT:] ** 2)); J1.append(np.mean(run_lms(ex, mu, 10 ** 9)[2][NT:] ** 2))
                out.append((st / up, 100 * (np.mean(J2) / np.mean(J1) - 1)))
            res[f"{ba}|{p}"] = dict(pred_nearest=pred_n, meas_nearest=out[0][0], dJ_nearest=out[0][1], pred_trunc=pred_t, meas_trunc=out[1][0], dJ_trunc=out[1][1])
            lg(f"   B_acc={ba:2d} mu=2^-{p:2d}: nearest  stall pred {pred_n:6.3f} meas {out[0][0]:6.3f}  MSE vs L1 {out[0][1]:+7.2f}%   |  truncation  stall pred {pred_t:6.3f} meas {out[1][0]:6.3f}  MSE vs L1 {out[1][1]:+7.2f}%")
    json.dump(res, open(f"{OUT}/T3.json", "w"))
    lg("   note: predictions use whole-run L1 statistics (training excluded); the stall count includes the training period of L2.")


def T4():
    """Tracking with finite precision: S*_MSE for mu in {2^-6, 2^-8, 2^-10}, B_mul = 12, B_acc in {16, 26, 32}; seeds 2000-2019
    (the first 20 FINAL L1 seeds -> paired with the final L1 data); 16 dB; L2 static baselines on the 11 nodes with the same seeds."""
    from freeze_grids import STATIC_C
    from sweep_analyse import s_star, interp_matrix
    S_SUB = [5000, 1000, 320, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5]; seeds = list(range(2000, 2020)); snr = 16.0; s2 = sigma_from_ebn0(snr) ** 2
    plat = plateau_stats(40, 116, s2)["eps_plateau"]; cg = np.array(STATIC_C); A = interp_matrix(cg, np.arange(40, 117))
    Jmin_cg = np.array([Rp_const(c, s2)[1] for c in cg]); rng = np.random.default_rng(5); BI = rng.integers(0, 20, (1000, 20))
    lg(f"T4 tracking, 16 dB, B_mul = 12, round to nearest, Gaussian noise, seeds 2000-2019 (paired with final L1), rho_th = 0.5; eps_plateau {plat:.3f}")
    res = {}
    for p in (6, 8, 10):
        mu = 2.0 ** -p
        for ba in (16, 26, 32, "L1"):
            Jst = []
            for cc in cg:
                c = np.full(NT + 152000, cc); v = []
                for sd in seeds:
                    ex, rq, dq = build(c, snr, sd)
                    v.append(np.mean((run_lms(ex, mu, 10 ** 9)[2] if ba == "L1" else run_fx(ex, rq, dq, p, 12, ba)[2])[NT:] ** 2))
                Jst.append(np.mean(v))
            Jst = np.array(Jst); rows = []
            for S in S_SUB:
                ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
                Jor = float(np.mean(oracle_J_series(taps_from_counter(c, H2), NT, NT + ne, s2)))
                w = np.bincount(c[NT:] - 40, minlength=77) / ne; eps_st = float(w @ (A @ (Jst - Jmin_cg)) / Jor)
                J3 = []; E3 = 0
                for sd in seeds:
                    ex, rq, dq = build(c, snr, sd)
                    if ba == "L1":
                        yA, yF, eA, eF, _ = run_lms(ex, mu, 10 ** 9)
                    else:
                        yA, yF, eA, eF, _, _, _ = run_fx(ex, rq, dq, p, 12, ba)
                    J3.append(np.mean(eA[NT:] ** 2)); E3 += int(ber_indicators(ex, yA, yF)[2][NT:].sum())
                J3 = np.array(J3); rho = ((J3 - Jor) / Jor - eps_st) / (plat - eps_st); m = rho[BI].mean(axis=1)
                rows.append(dict(S=S, rho=float(rho.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), eps=float(((J3 - Jor) / Jor).mean()), ber=E3 / (20 * ne)))
            sts = ["P" if r["hi"] < 0.5 else ("F" if r["lo"] > 0.5 else "?") for r in rows]
            Sst = s_star(sts, S_SUB, strict=False)
            res[f"{p}|{ba}"] = dict(rows=rows, status="".join(sts), S_star=Sst[0], mono=Sst[1], eps_static_node=list(map(float, (Jst - Jmin_cg) / Jmin_cg)))
            lg(f"   mu=2^-{p:2d} {'L1 (float)' if ba == 'L1' else f'B_acc={ba}':10s}: rho " + " ".join(f"{r['rho']:5.2f}" for r in rows) + f"   status {''.join(sts)}  S*_MSE {Sst[0]}  (static excess c=40/116: {100*res[f'{p}|{ba}']['eps_static_node'][0]:.1f}/{100*res[f'{p}|{ba}']['eps_static_node'][-1]:.1f} %)")
    lg("   S grid: " + " ".join(str(S) for S in S_SUB))
    json.dump(res, open(f"{OUT}/T4.json", "w"), default=float)
    # coefficient trajectories, fixed vs float (PPR-22 Sec. 6.2 detection method), one case
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    S = 28; ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S); ex, rq, dq = build(c, snr, 2000)
    fig, ax = plt.subplots(figsize=(10, 4)); t = np.arange(0, NT + ne, 50)
    w1 = run_lms(ex, 2.0 ** -10, 50)[4]; ax.plot(t[:len(w1)] - NT, w1[:, 1], "k", lw=1.2, label="L1 float")
    for ba, col in ((16, "tab:red"), (26, "tab:blue"), (32, "tab:green")):
        wf = run_fx(ex, rq, dq, 10, 12, ba, 1, 50)[4]; ax.plot(t[:len(wf)] - NT, wf[:, 1], color=col, lw=0.8, label=f"L2 B_mul=12, B_acc={ba}")
    ax.set_xlim(-2000, 4 * 152 * S); ax.set_xlabel("symbols after training"); ax.set_ylabel("R3 coefficient w_1"); ax.legend(fontsize=8)
    ax.set_title("P6a T4: coefficient trajectory, fixed point vs floating point (mu = 2^-10, S = 28, 16 dB; L2 simulation)", fontsize=9)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_P6a_T4_coefficients.png", dpi=120)


def poly_is_primitive(n, k):
    """x^n + x^k + 1 over GF(2) is primitive iff x^(2^n-1) = 1 and x^((2^n-1)/q) != 1 for every prime q | 2^n-1."""
    P = (1 << n) | (1 << k) | 1
    def mulmod(a, b):
        r = 0
        while b:
            if b & 1: r ^= a
            b >>= 1; a <<= 1
            if a >> n & 1: a ^= P
        return r
    def powx(e):
        r, base = 1, 2
        while e:
            if e & 1: r = mulmod(r, base)
            base = mulmod(base, base); e >>= 1
        return r
    N = (1 << n) - 1; m = N; qs = []; q = 2
    while q * q <= m:
        while m % q == 0:
            qs.append(q); m //= q
        q += 1
    if m > 1: qs.append(m)
    return powx(N) == 1 and all(powx(N // q) != 1 for q in set(qs))


def irwin_hall_sf(t, n=12):
    x = Fraction(t).limit_denominator(10 ** 7) + Fraction(n, 2)
    if x >= n: return 0.0
    return float(1 - sum((-1) ** k * comb(n, k) * (x - k) ** n for k in range(int(x) + 1)) / factorial(n))


def T5():
    lg("T5 FPGA-style noise generator (12 LFSRs, distinct trinomials, 16 bits each, sum of 12 uniforms; PPR-22 Sec. 4.3)")
    prim = [(int(n), int(k), poly_is_primitive(int(n), int(k))) for n, k in LFSR_TAPS]
    lg("   primitivity (algebraic order test): " + ", ".join(f"x^{n}+x^{k}+1 {'yes' if ok else 'NO'}" for n, k, ok in prim))
    from numba import njit
    @njit
    def period(nb, kb):
        st = 1; s0 = 1; i = 0
        while True:
            fb = ((st >> 0) ^ (st >> (nb - kb))) & 1; st = (st >> 1) | (fb << (nb - 1)); i += 1
            if st == s0: return i
    for n, k, _ in prim[:3]:
        lg(f"   empirical period of the n = {n} register: {period(n, k)} (2^n - 1 = {(1 << n) - 1})")
    v = lfsr_noise(4_000_000, 1.0, 12345); w = lfsr_noise(4_000_000, 1.0, 54321)
    ac = [np.dot(v[:-k], v[k:]) / np.dot(v, v) for k in range(1, 51)]
    kurt = np.mean(v ** 4) / np.mean(v ** 2) ** 2 - 3
    lg(f"   4e6 samples: mean {v.mean():+.2e}  variance {v.var():.5f} (target 1)  max |autocorr| lag 1-50 {max(abs(np.array(ac))):.1e} (4/sqrt(N) = {4/np.sqrt(len(v)):.1e})")
    lg(f"   cross-correlation between two seeds {np.dot(v, w)/np.sqrt(np.dot(v, v)*np.dot(w, w)):+.1e};  max |v| {np.abs(v).max():.3f} sigma (support limit 6);  excess kurtosis {kurt:+.3f} (Irwin-Hall n=12: -0.100; Gaussian 0)")
    lg(f"   P(v > 3 sigma) {np.mean(v > 3):.2e}  (Irwin-Hall {irwin_hall_sf(3):.2e}, Gaussian {norm.sf(3):.2e});  repeatable: {np.array_equal(v[:1000], lfsr_noise(1000, 1.0, 12345))}")
    lg("   BER of the direct detector on a FLAT channel with this noise (2e8 bits per point): measured vs exact Irwin-Hall prediction vs Gaussian Q")
    res = {}
    for i, e in enumerate((6.0, 8.0, 9.0)):
        sig = sigma_from_ebn0(e); k = 0; N = 0
        for blk in range(20):
            n = 10_000_000; b = make_bits(n, 910000 + 100 * i + blk); x = 2.0 * b - 1
            r = x + lfsr_noise(n, sig, 920000 + 100 * i + blk); k += int(np.sum((r >= 0) != (b == 1))); N += n
        ih = irwin_hall_sf(1 / sig); g = norm.sf(1 / sig)
        lo, hi = [float(q) for q in __import__("scipy.stats", fromlist=["binomtest"]).binomtest(k, N).proportion_ci(0.95)]
        res[e] = dict(k=k, N=N, ih=ih, gauss=g)
        lg(f"   {e:4.1f} dB: measured {k/N:.3e} [{lo:.3e}, {hi:.3e}] ({k} errors)   Irwin-Hall exact {ih:.3e}   Gaussian {g:.3e}   (measured/Gaussian {k/N/g:.2f})")
    json.dump(dict(primitive=prim, ber=res), open(f"{OUT}/T5.json", "w"), default=float)


def T6():
    """Reference vectors for RTL verification (P8): baseline B_mul = 12, B_acc = 26, round to nearest, mu = 2^-8, S = 20, 14 dB, LFSR noise."""
    S = 20; p = 8; n_tot = NT + 4000; c = triangle_counter(n_tot, NT, 40, 116, S)
    ex, rq, dq = build(c, 14.0, 2000, noise="lfsr")
    yA, yF, eA, eF, wH, st, up = fxp_receivers(rq, dq, L, p, NT, BM0, BA0, 1, 100)
    hdr = "n,c,r_q,d_q,yA_q,eA_q,yF_q,eF_q"
    np.savetxt(f"{OUT}/T6_vectors.csv", np.column_stack([np.arange(n_tot), c, rq, dq, yA, eA, yF, eF]).astype(np.int64), fmt="%d", delimiter=",", header=hdr, comments="")
    np.savetxt(f"{OUT}/T6_coeff_every100.csv", np.round(wH * (1 << (BM0 - 2))).astype(np.int64), fmt="%d", delimiter=",", header=",".join(f"w{k}_q" for k in range(L)), comments="")
    json.dump(dict(formats="r,u,d,y,e: s16.12; multiplier coeff s12.10; accumulator s26.24; round to nearest; saturation everywhere",
                   mu="2^-8 (shift 8)", L=L, Delta=DELTA, N_T=NT, S=S, EbN0=14.0, seed=2000, noise="12-LFSR sum of uniforms (fxp_lib.lfsr_noise)",
                   rows=n_tot, stalls=int(st), updates=int(up)), open(f"{OUT}/T6_vectors_README.json", "w"), indent=1)
    lg(f"T6 vectors exported: {n_tot} symbols (training {NT} + 4000 payload), columns {hdr}; coefficients every 100 symbols; BER R3 in payload "
       f"{np.mean(((yA[NT+DELTA:] >= 0).astype(int)) != ex['bits'][NT:n_tot-DELTA]):.2e}")




def T4b():
    """Tracking vs MULTIPLIER width: B_mul in {8, 12, 16}, B_acc = 26, mu = 2^-8, 16 dB, same design as T4 (seeds 2000-2019)."""
    global lines
    from freeze_grids import STATIC_C
    from sweep_analyse import s_star, interp_matrix
    S_SUB = [5000, 1000, 320, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5]; seeds = list(range(2000, 2020)); snr = 16.0; s2 = sigma_from_ebn0(snr) ** 2; p = 8
    plat = plateau_stats(40, 116, s2)["eps_plateau"]; cg = np.array(STATIC_C); A = interp_matrix(cg, np.arange(40, 117))
    Jmin_cg = np.array([Rp_const(c, s2)[1] for c in cg]); rng = np.random.default_rng(5); BI = rng.integers(0, 20, (1000, 20)); res = {}
    lg("T4b tracking vs multiplier width (B_acc = 26, mu = 2^-8, 16 dB, seeds 2000-2019, round to nearest)")
    for bm in (8, 12, 16):
        Jst = np.array([np.mean([np.mean(run_fx(*build(np.full(NT + 152000, cc), snr, sd), p, bm, 26)[2][NT:] ** 2) for sd in seeds]) for cc in cg])
        rows = []
        for S in S_SUB:
            ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
            Jor = float(np.mean(oracle_J_series(taps_from_counter(c, H2), NT, NT + ne, s2)))
            w = np.bincount(c[NT:] - 40, minlength=77) / ne; eps_st = float(w @ (A @ (Jst - Jmin_cg)) / Jor)
            J3 = np.array([np.mean(run_fx(*build(c, snr, sd), p, bm, 26)[2][NT:] ** 2) for sd in seeds])
            rho = ((J3 - Jor) / Jor - eps_st) / (plat - eps_st); m = rho[BI].mean(axis=1)
            rows.append(dict(S=S, rho=float(rho.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), eps=float(((J3 - Jor) / Jor).mean())))
        sts = ["P" if r["hi"] < 0.5 else ("F" if r["lo"] > 0.5 else "?") for r in rows]; Sst = s_star(sts, S_SUB, strict=False)
        res[bm] = dict(rows=rows, status="".join(sts), S_star=Sst[0], eps_static_node=list(map(float, (Jst - Jmin_cg) / Jmin_cg)))
        lg(f"   B_mul={bm:2d}: eps(%) " + " ".join(f"{100*r['eps']:5.0f}" for r in rows) + f"\n             rho    " + " ".join(f"{r['rho']:5.2f}" for r in rows) + f"   status {''.join(sts)}  S*_MSE {Sst[0]}")
    json.dump(res, open(f"{OUT}/T4b.json", "w"), default=float)


def T7():
    """Reacquisition time vs word length: P2 large_up (c 40 -> 116), mu = 2^-8, 16 dB, N_T = 60000 (as final P2), 20 seeds 2000-2019."""
    N_T2, N_PRE, N_POST, W, KAPPA = 60000, 20000, 60000, 64, 0.25; N_C = N_T2 + N_PRE; p = 8; seeds = list(range(2000, 2100)); snr = 16.0
    lg("T7 reacquisition time N_rec (kappa 0.25, W 64, post-transition static reference of the SAME arithmetic), large_up, mu = 2^-8, 16 dB, 100 seeds 2000-2099 (20 seeds gave a noise-dominated last-crossing time; see log of the first attempt)")
    def nrec(mean_e2, thr):
        cs = np.cumsum(np.insert(mean_e2, 0, 0.0)); ma = (cs[W:] - cs[:-W]) / W; bad = np.nonzero(ma > thr)[0]
        return 0 if len(bad) == 0 else int(bad[-1] + 1)
    c = step_counter(40, 116, N_T2, N_PRE, N_POST); cB = np.full(N_T2 + 200000, 116)
    for cfg in [(None, None)] + [(bm, ba) for bm in (8, 12, 16) for ba in (16, 26, 32)]:
        bm, ba = cfg; acc = np.zeros(len(c)); refv = []
        for sd in seeds:
            ex = make_exp_from_counter(c, N_T2, snr, sd); d = delayed_symbols(ex["x"], DELTA)
            exB = make_exp_from_counter(cB, N_T2, snr, sd); dB = delayed_symbols(exB["x"], DELTA)
            if bm is None:
                eA = lms_receivers(ex["r"], d, L, 2.0 ** -p, N_T2, 0, 10 ** 9)[2]; eB = lms_receivers(exB["r"], dB, L, 2.0 ** -p, N_T2, 0, 10 ** 9)[2]
            else:
                eA = fxp_receivers(quantize_signal(ex["r"]), quantize_signal(d), L, p, N_T2, bm, ba, 1, 10 ** 9)[2] / 4096.0
                eB = fxp_receivers(quantize_signal(exB["r"]), quantize_signal(dB), L, p, N_T2, bm, ba, 1, 10 ** 9)[2] / 4096.0
            acc += eA ** 2; refv.append(np.mean(eB[-150000:] ** 2))
        acc /= len(seeds); Jss = float(np.mean(refv))
        k = nrec(acc[N_C - (W - 1):], (1 + KAPPA) * Jss)
        lg(f"   {'L1 float' if bm is None else f'B_mul={bm:2d} B_acc={ba:2d}':18s}: post-transition static MSE {Jss:.5f}   N_rec {k:6d} symbols")


if __name__ == "__main__":
    t0 = time.time(); name = sys.argv[1]; globals()[name]()
    lg(f"[{name} done in {time.time()-t0:.0f} s]")
    open(f"{OUT}/{name}_log.txt", "w").write("\n".join(lines))
