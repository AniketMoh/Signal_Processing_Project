# p1_validation.py -- Phase P1: floating-point static LMS, validation tests V0-V7 (level L1).
# Every test prints PASS / FAIL with the measured numbers. Figures and a JSON log go to results/.
# Pilot seeds only (1000-1099). No tracking result is claimed here.
import json, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import binomtest

from config import CFG, DA, sigma_from_ebn0
from lms_lib import (make_bits, lfsr_bits, bpsk, make_noise, make_experiment, run_receivers, delayed_symbols,
                     count_errors, oracle_at, oracle_mean, r1_exact_ber, bpsk_theory, taps_from_counter,
                     triangle_counter)

L, M, H2 = CFG["L"], CFG["M"], CFG["h2"]
LOG = {"params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in CFG.items() if k not in ("pilot_seeds", "final_seeds")},
       "tests": {}}
C_MILD_HI, C_PRIM_LO, C_PRIM_HI = CFG["mild"][1], CFG["primary"][0], CFG["primary"][1]
MU = 2.0 ** -8                      # default step size for the static tests
BLUE, ORANGE, AQUA, INK, INK2, GRID = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#52514e", "#e3e2de"


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.xaxis.label.set_color(INK2); ax.yaxis.label.set_color(INK2); ax.title.set_color(INK)


def verdict(name, ok, text):
    LOG["tests"][name] = {"pass": bool(ok), "detail": text}
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {text}")


def const_taps(c):
    """taps array with one row, for the oracle of a constant channel"""
    return taps_from_counter(np.array([c]), H2)


def oracle_const(c, Delta, sigma2):
    return oracle_at(const_taps(c), 0, L, Delta, sigma2, quasi_static=True)


# ------------------------------------------------------------------ V0
def test_V0():
    a = make_experiment(None, CFG["mild"], 14, 1000, N_T=3000, N_eval=3000)
    b = make_experiment(None, CFG["mild"], 14, 1000, N_T=3000, N_eval=3000)
    c = make_experiment(None, CFG["mild"], 14, 1001, N_T=3000, N_eval=3000)
    oa, ob = run_receivers(a, 2, MU), run_receivers(b, 2, MU)
    same = np.array_equal(a["r"], b["r"]) and np.array_equal(oa["y3"], ob["y3"])
    diff = not np.array_equal(a["r"], c["r"])
    # the same seed must give the same bits and noise whatever mu, Delta, S are (fair comparison)
    d = make_experiment(None, CFG["mild"], 14, 1000, N_T=3000, N_eval=3000)
    fair = np.array_equal(a["bits"], d["bits"]) and np.array_equal(a["r"], d["r"])
    verdict("V0 reproducibility", same and diff and fair, f"same seed identical={same}, other seed differs={diff}, receiver settings do not change data={fair}")


# ------------------------------------------------------------------ V1
def test_V1():
    N = 1_000_000
    sig = sigma_from_ebn0(14)
    v = make_noise(N, sig, 1)
    mean_ok = abs(v.mean()) < 4 * sig / np.sqrt(N)
    var_rel = v.var() / sig ** 2 - 1
    ac = [np.dot(v[:-k], v[k:]) / np.dot(v, v) for k in range(1, 51)]
    ac_ok = max(abs(np.array(ac))) < 4 / np.sqrt(N)
    tail = np.mean(np.abs(v) > 3 * sig)
    tail_ok = abs(tail - 0.0026998) < 4 * np.sqrt(0.0027 * 0.9973 / N)
    other = make_noise(N, sig, 2)
    cross = abs(np.dot(v, other) / np.sqrt(np.dot(v, v) * np.dot(other, other)))
    rep = np.array_equal(v, make_noise(N, sig, 1))
    ok = mean_ok and abs(var_rel) < 0.01 and ac_ok and tail_ok and cross < 4 / np.sqrt(N) and rep
    verdict("V1 noise generator", ok,
            f"mean/sigma={v.mean()/sig:.2e}, var error={100*var_rel:.3f}%, max |autocorr| lag1-50={max(abs(np.array(ac))):.1e} (limit {4/np.sqrt(N):.1e}), "
            f"P(|v|>3sigma)={tail:.5f} (theory 0.00270), max|v|/sigma={abs(v).max()/sig:.2f}, cross-seed corr={cross:.1e}, repeatable={rep}. "
            "Note: this is the numpy Gaussian source of L1; the LFSR-sum generator is validated in P6.")


# ------------------------------------------------------------------ V2
def test_V2():
    ebn0s = np.linspace(0.0, 8.25, 12)
    N = 2_000_000
    meas, lo95, hi95, lo99, hi99, theory, in95, in99 = [], [], [], [], [], [], [], []
    for i, e in enumerate(ebn0s):
        bits = make_bits(N, 7000 + i)
        r = bpsk(bits) + make_noise(N, sigma_from_ebn0(e), 8000 + i)
        k = int(np.sum((r >= 0).astype(int) != bits))
        p0 = float(bpsk_theory(e))
        bt = binomtest(k, N, p0)
        c95, c99 = bt.proportion_ci(0.95), bt.proportion_ci(0.99)
        meas.append(k / N); theory.append(p0)
        lo95.append(c95.low); hi95.append(c95.high); lo99.append(c99.low); hi99.append(c99.high)
        in95.append(c95.low <= p0 <= c95.high); in99.append(c99.low <= p0 <= c99.high)
        print(f"   Eb/N0={e:5.2f} dB  errors={k:7d}  BER={k/N:.3e}  theory={p0:.3e}  in95={in95[-1]}  in99={in99[-1]}")
    ok = all(in99) and min(int(m * N) for m in meas) >= 100
    verdict("V2 flat-channel BER vs theory", ok, f"{sum(in95)}/12 points inside the 95% interval, {sum(in99)}/12 inside the 99% interval, min errors per point = {min(int(m*N) for m in meas)}")
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    fine = np.linspace(0, 9, 200)
    ax.semilogy(fine, bpsk_theory(fine), color=INK2, lw=1.6, label="theory Q(sqrt(2Eb/N0))")
    m = np.array(meas)
    ax.errorbar(ebn0s, m, yerr=[m - np.array(lo95), np.array(hi95) - m], fmt="o", color=BLUE, ms=5, lw=1.2, capsize=2, label="measured, 95% interval (2e6 bits each)")
    ax.set_xlabel("Eb/N0 (dB)"); ax.set_ylabel("BER"); ax.set_title("V2: flat channel, no equalizer (L1 simulation)", fontsize=11)
    ax.legend(frameon=False, fontsize=9); style(ax)
    fig.tight_layout(); fig.savefig("results/fig_V2_flat_ber.png", dpi=160); plt.close(fig)


# ------------------------------------------------------------------ V5 (done early because Delta is needed by the other tests)
def choose_delta():
    """One fixed Delta for the whole project: the smallest Delta whose oracle MSE is within 2% of the best Delta
    at every coefficient value of the primary trajectory and both pilot SNRs."""
    cs = list(range(C_PRIM_LO, C_PRIM_HI + 1, 4)) + [C_PRIM_HI]
    worst = np.zeros(L + M - 1)
    for e in CFG["ebn0_pilot"]:
        s2 = sigma_from_ebn0(e) ** 2
        for c in cs:
            J = np.array([oracle_const(c, D, s2)[1] for D in range(L + M - 1)])
            worst = np.maximum(worst, J / J.min() - 1)
    ok = np.where(worst <= 0.02)[0]
    return (int(ok[0]) if len(ok) else int(np.argmin(worst))), worst


def test_V5():
    Dfix, worst = choose_delta()
    cases = [("a=0.60, 14 dB", C_MILD_HI, 14.0), ("a=0.60, 16 dB", C_MILD_HI, 16.0),
             ("a=0.91, 14 dB", C_PRIM_HI, 14.0), ("a=0.91, 16 dB", C_PRIM_HI, 16.0)]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0), sharey=True)
    rows = {}
    for idx, (name, c, e) in enumerate(cases):
        s2 = sigma_from_ebn0(e) ** 2
        Jor = [oracle_const(c, D, s2)[1] for D in range(L + M - 1)]
        Jlms = []
        for D in range(L + M - 1):
            exp = make_experiment(None, (c, c), e, 1000, N_T=30000, N_eval=60000)
            out = run_receivers(exp, D, MU)
            Jlms.append(float(np.mean(out["e3"][-30000:] ** 2)))
        rows[name] = dict(J_oracle=Jor, J_lms=Jlms)
        ax = axes[0 if c == C_MILD_HI else 1]
        col = BLUE if e == 14.0 else ORANGE
        ax.semilogy(range(L + M - 1), Jor, "-", color=col, lw=1.6, label=f"{int(e)} dB oracle")
        ax.semilogy(range(L + M - 1), Jlms, "o", color=col, ms=4, mfc="none", label=f"{int(e)} dB LMS")
    for ax, t in zip(axes, ["control channel, a = 0.60", "primary channel, a = 0.91 (top of range)"]):
        ax.axvline(Dfix, color=AQUA, lw=1.2, ls="--"); ax.set_title(t, fontsize=10.5); ax.set_xlabel("decision delay Delta"); style(ax)
    axes[0].set_ylabel("MSE"); axes[0].text(Dfix + 0.2, 0.5, f"chosen Delta = {Dfix}", color=AQUA, fontsize=9)
    axes[1].legend(frameon=False, fontsize=8, loc="lower right", ncol=2)
    fig.suptitle("V5: MSE vs decision delay (lines = analytic oracle, circles = LMS, mu = 2^-8, L = 16)", fontsize=10.5, color=INK)
    fig.tight_layout(); fig.savefig("results/fig_V5_delta_sweep.png", dpi=160); plt.close(fig)
    best_lms = {k: int(np.argmin(v["J_lms"])) for k, v in rows.items()}
    best_or = {k: int(np.argmin(v["J_oracle"])) for k, v in rows.items()}
    LOG["delta"] = dict(chosen=Dfix, worst_excess_over_best_delta=[float(w) for w in worst], best_delta_oracle=best_or, best_delta_lms=best_lms, rows=rows)
    ok = all(abs(rows[k]["J_lms"][Dfix] / rows[k]["J_oracle"][Dfix] - 1) < 0.25 for k in rows)
    verdict("V5 delay sweep", ok, f"chosen Delta={Dfix} (within {100*worst[Dfix]:.2f}% of the best Delta everywhere on the primary trajectory at 14 and 16 dB); "
            f"oracle argmin per case={best_or}; LMS argmin per case={best_lms}")
    return Dfix


# ------------------------------------------------------------------ V3
def test_V3(Dfix):
    exp = make_experiment(None, (C_MILD_HI, C_MILD_HI), 14, 1000, N_T=30000, N_eval=200000)
    out = run_receivers(exp, Dfix, MU)
    N_T, n_tot = exp["N_T"], exp["n_total"]
    x = exp["x"]
    lags = np.arange(-5, 26)
    def xc(y):
        d = np.where(y[N_T:n_tot] >= 0, 1.0, -1.0)
        return np.array([np.mean(d[max(0, l) : len(d) + min(0, l)] * x[N_T - l + max(0, l) : n_tot - l + max(0, l) - max(0, l) + (0)][: len(d) - abs(l)]) for l in lags])
    # simple, explicit version of the correlation:  C(l) = mean( sign(y[n]) * x[n-l] )
    def xcorr(y):
        n = np.arange(N_T + 30, n_tot - 30)
        d = np.where(y[n] >= 0, 1.0, -1.0)
        return np.array([np.mean(d * x[n - l]) for l in lags])
    c3, c1 = xcorr(out["y3"]), xcorr(out["y1"])
    peak3, peak1 = int(lags[np.argmax(c3)]), int(lags[np.argmax(c1)])
    ber_ok = count_errors(out["y3"], exp["bits"], Dfix, N_T, n_tot)
    wrong = {dl: count_errors(out["y3"], exp["bits"], dl, N_T, n_tot)[0] / (n_tot - N_T) for dl in (0, Dfix + 1, Dfix + 3) if dl != Dfix}
    ok = peak3 == Dfix and peak1 == 0 and all(abs(b - 0.5) < 0.01 for b in wrong.values())
    verdict("V3 alignment", ok, f"R3 correlation peak at lag {peak3} (Delta={Dfix}), R1 peak at lag {peak1}; BER with correct delay={ber_ok[0]}/{ber_ok[1]}; BER with wrong delays {({k: round(v, 3) for k, v in wrong.items()})}")


# ------------------------------------------------------------------ V4
def white_input_control():
    """Control for the misadjustment formula: flat channel + white Gaussian input, where the textbook formula is exact.
    If this matches, the measurement pipeline (error definition, window, J_min) is correct."""
    sig = sigma_from_ebn0(14.0); s2 = sig ** 2
    out = {}
    for k in (8, 9, 10):
        mu = 2.0 ** -k
        ex = []
        for seed in range(1000, 1003):
            rng = np.random.default_rng(seed)
            x = rng.standard_normal(1_030_000)
            r = x + make_noise(len(x), sig, seed + 99)
            from lms_lib import lms_receivers
            _, _, eA, _, _ = lms_receivers(r, delayed_symbols(x, 0), L, mu, 30000, 0, 64)
            ex.append(np.mean(eA[-900000:] ** 2) / (s2 / (1 + s2)) - 1)
        q = mu * L * (1 + s2) / 2
        out[k] = (float(np.mean(ex)), q / (1 - q))
    return out


def test_V4(Dfix):
    e = 14.0
    s2 = sigma_from_ebn0(e) ** 2
    c = C_MILD_HI
    w_or, J_or = oracle_const(c, Dfix, s2)
    a = c * DA
    trR = L * (1 + a * a + H2 * H2 + s2)
    rows = []
    for k in (8, 9, 10):
        mu = 2.0 ** -k
        ex, errs = [], []
        for seed in range(1000, 1004):
            exp = make_experiment(None, (c, c), e, seed, N_T=30000, N_eval=1_000_000)
            out = run_receivers(exp, Dfix, mu, hist_stride=64)
            wbar = out["wH"][-(500000 // 64):].mean(axis=0)
            errs.append(np.linalg.norm(wbar - w_or) / np.linalg.norm(w_or))
            ex.append(np.mean(out["e3"][-900000:] ** 2) / J_or - 1)
            if k == 8 and seed == 1000:
                wb8 = wbar
        q = mu * trR / 2
        rows.append(dict(k=k, coef_rel_err=float(np.mean(errs)), excess_meas=float(np.mean(ex)), excess_sem=float(np.std(ex, ddof=1) / 2), excess_theory=q / (1 - q)))
        r = rows[-1]
        print(f"   mu=2^-{k}: coefficient error {100*r['coef_rel_err']:.2f}%, excess MSE {100*r['excess_meas']:.2f}% (+-{100*r['excess_sem']:.2f}), textbook formula {100*r['excess_theory']:.2f}%, ratio {r['excess_meas']/r['excess_theory']:.2f}")
    ctrl = white_input_control()
    LOG["V4_rows"] = rows
    LOG["V4_white_control"] = {str(k): dict(measured=v[0], theory=v[1]) for k, v in ctrl.items()}
    ok_a = all(r["coef_rel_err"] < 0.05 for r in rows)
    verdict("V4a LMS coefficients vs Wiener", ok_a, "; ".join(f"mu=2^-{r['k']}: {100*r['coef_rel_err']:.2f}%" for r in rows))
    ok_b = all(abs(r["excess_meas"] / r["excess_theory"] - 1) < 0.20 for r in rows)
    verdict("V4b excess MSE vs textbook formula mu*tr(R)/2/(1-mu*tr(R)/2)", ok_b,
            "; ".join(f"mu=2^-{r['k']}: {100*r['excess_meas']:.2f}% vs {100*r['excess_theory']:.2f}% (x{r['excess_meas']/r['excess_theory']:.2f})" for r in rows)
            + ". Criterion was within 20%. See finding F-1: the formula underestimates for this ISI channel.")
    ok_c = all(abs(v[0] / v[1] - 1) < 0.05 for v in ctrl.values()) and \
        all(abs(rows[i]["excess_meas"] / rows[i + 1]["excess_meas"] - 2) < 0.3 for i in range(2))
    verdict("V4c pipeline control and linear scaling in mu", ok_c,
            "white-input flat channel matches the formula " + ", ".join(f"2^-{k}: {100*v[0]:.2f}% vs {100*v[1]:.2f}%" for k, v in ctrl.items())
            + f"; ISI-channel excess ratios between successive mu = {rows[0]['excess_meas']/rows[1]['excess_meas']:.2f}, {rows[1]['excess_meas']/rows[2]['excess_meas']:.2f} (ideal 2)")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    k = np.arange(L)
    ax.bar(k - 0.2, w_or, 0.4, color=BLUE, label="Wiener (oracle) coefficients")
    ax.bar(k + 0.2, wb8, 0.4, color=ORANGE, label="LMS coefficients (average of last 500k symbols)")
    ax.set_xlabel("tap index k"); ax.set_ylabel("w_k"); ax.set_title("V4a: static channel a = 0.60, 14 dB, mu = 2^-8", fontsize=11)
    ax.legend(frameon=False, fontsize=9); style(ax)
    fig.tight_layout(); fig.savefig("results/fig_V4_coefficients.png", dpi=160); plt.close(fig)


# ------------------------------------------------------------------ V6
def test_V6(Dfix):
    N = 32767
    b = lfsr_bits(N)
    x = bpsk(b)
    bal = int(b.sum())
    ac = np.array([np.dot(x, np.roll(x, -k)) / N for k in range(0, 60)])
    offpeak = float(np.max(np.abs(ac[1:])))
    # LMS trained on PRBS vs alternating pattern, then frozen (R2) and tested on random data, static channel
    e = 14.0
    s2 = sigma_from_ebn0(e) ** 2
    c = C_MILD_HI
    J_or = oracle_const(c, Dfix, s2)[1]
    res = {}
    for tr in ("prbs", "alt"):
        exp = make_experiment(None, (c, c), e, 1000, N_T=30000, N_eval=50000, training=tr)
        out = run_receivers(exp, Dfix, MU)
        res[tr] = float(np.mean(out["e2"][-30000:] ** 2))
    ok = bal == 16384 and abs(offpeak - 1 / N) < 1e-9 and res["prbs"] < 1.5 * J_or and res["alt"] > 5 * J_or
    verdict("V6 training excitation", ok, f"PRBS ones={bal} (expect 16384), max off-peak autocorrelation={offpeak:.2e} (theory {1/N:.2e}); frozen-filter MSE on random data: PRBS-trained {res['prbs']:.4f}, "
            f"alternating-trained {res['alt']:.4f}, oracle {J_or:.4f}")
    # learning curves (also checks that N_T = 30000 is long enough)
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    out_conv = {}
    for k, col in zip((7, 8, 9, 10), (BLUE, ORANGE, AQUA, INK2)):
        mu = 2.0 ** -k
        exp = make_experiment(None, (C_PRIM_LO, C_PRIM_LO), e, 1000, N_T=30000, N_eval=2000)
        out = run_receivers(exp, Dfix, mu)
        e2 = out["e3"][:30000] ** 2
        W = 500
        sm = np.convolve(e2, np.ones(W) / W, mode="valid")
        Jfin = np.mean(e2[-5000:])
        n_conv = int(np.argmax(sm <= 1.1 * Jfin)) + W
        out_conv[k] = n_conv
        ax.semilogy(np.arange(len(sm)) + W, sm, color=col, lw=1.3, label=f"mu = 2^-{k}")
    ax.axhline(oracle_const(C_PRIM_LO, Dfix, s2)[1], color=INK2, lw=1, ls="--")
    ax.text(600, oracle_const(C_PRIM_LO, Dfix, s2)[1] * 0.8, "oracle MSE", color=INK2, fontsize=9)
    ax.set_xlim(0, 12000); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_xlabel("symbol index n (training on the PRBS)"); ax.set_ylabel("MSE (500-symbol moving average)")
    ax.set_title("Learning curves, a = 0.3125, 14 dB, one seed (pilot)", fontsize=11); style(ax)
    fig.tight_layout(); fig.savefig("results/fig_P1_learning_curves.png", dpi=160); plt.close(fig)
    LOG["convergence_symbols_to_within_10pct"] = out_conv
    print(f"   symbols until the moving-average MSE is within 10% of its final value: {out_conv}  (N_T = {CFG['N_T']})")


# ------------------------------------------------------------------ V2b
def test_V2b(Dfix):
    N_eval = 1_000_000
    ebs = [6.0, 8.0, 10.0, 12.0, 14.0, 16.0]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    summary = {}
    ok_all = True
    for ax, (name, c) in zip(axes, [("control a = 0.60", C_MILD_HI), ("primary a = 0.91", C_PRIM_HI)]):
        b1, b2, b3, ex = [], [], [], []
        for e in ebs:
            exp = make_experiment(None, (c, c), e, 1000, N_T=30000, N_eval=N_eval)
            out = run_receivers(exp, Dfix, MU)
            n0, n1 = exp["N_T"], exp["n_total"]
            e1 = count_errors(out["y1"], exp["bits"], 0, n0, n1)[0]
            e2 = count_errors(out["y2"], exp["bits"], Dfix, n0, n1)[0]
            e3 = count_errors(out["y3"], exp["bits"], Dfix, n0, n1)[0]
            floor = 3.0 / N_eval
            b1.append(max(e1 / N_eval, floor)); b2.append(max(e2 / N_eval, floor)); b3.append(max(e3 / N_eval, floor))
            ex.append(r1_exact_ber(c * DA, H2, sigma_from_ebn0(e)))
            print(f"   {name} {e:4.1f} dB: errors R1={e1} R2={e2} R3={e3}  (of {N_eval});  R1 exact={ex[-1]:.3e}")
            # R1 must agree with the exact formula when enough errors were counted
            if e1 >= 100:
                p = binomtest(e1, N_eval, ex[-1]).pvalue
                ok_all = ok_all and p > 0.001
        ax.semilogy(ebs, bpsk_theory(np.array(ebs)), color=GRID, lw=2.5, label="flat channel, no ISI")
        ax.semilogy(ebs, ex, "-", color=BLUE, lw=1.2)
        ax.semilogy(ebs, b1, "o", color=BLUE, ms=5, label="R1 direct (line = exact formula)")
        ax.semilogy(ebs, b2, "s", color=ORANGE, ms=5, mfc="none", label="R2 frozen LMS")
        ax.semilogy(ebs, b3, "^", color=AQUA, ms=5, mfc="none", label="R3 adaptive LMS")
        ax.set_ylim(1.5e-6, 1.0); ax.set_title(name, fontsize=10.5); ax.set_xlabel("Eb/N0 (dB)"); style(ax)
        summary[name] = dict(ebn0=ebs, R1=b1, R2=b2, R3=b3, R1_exact=ex)
    axes[0].set_ylabel("BER (points at 3e-6 = zero errors, upper bound 3/N)"); axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("V2b: static ISI channels (L1), 1e6 payload bits per point, mu = 2^-8", fontsize=10.5, color=INK)
    fig.tight_layout(); fig.savefig("results/fig_V2b_static_isi.png", dpi=160); plt.close(fig)
    LOG["V2b"] = summary
    # equalization must reduce R1's error floor on the closed-eye channel
    b1h, b3h = summary["primary a = 0.91"]["R1"][-1], summary["primary a = 0.91"]["R3"][-1]
    verdict("V2b static ISI", ok_all and b3h < 0.05 * b1h, f"R1 matches the exact 4-pattern formula (where >=100 errors); at 16 dB on a=0.91: R1 BER={b1h:.3e}, R3 BER <= {b3h:.1e}")


# ------------------------------------------------------------------ V7
def test_V7(Dfix):
    e = 14.0
    sig = sigma_from_ebn0(e); s2 = sig ** 2
    # (a) Monte-Carlo check of the oracle on a FAST ramp (S = 1): the channel moves inside the window
    exp = make_experiment(1, CFG["primary"], e, 1000, N_T=1000, N_eval=3000)
    taps = exp["taps"]
    n = 2000
    w_ex, J_ex = oracle_at(taps, n, L, Dfix, s2)
    w_qs, J_qs = oracle_at(taps, n, L, Dfix, s2, quasi_static=True)
    F = L + M - 1
    K = 300000
    rng = np.random.default_rng(31337)
    xf = 2.0 * rng.integers(0, 2, (K, F)) - 1.0
    tf = taps[n - F + 1 : n + 1]                  # taps active at the F times n-F+1 ... n
    rf = np.zeros((K, F))
    for t in range(F):
        for k in range(M):
            if t - k >= 0:
                rf[:, t] += tf[t, k] * xf[:, t - k]
    rf += sig * rng.standard_normal((K, F))
    u = rf[:, ::-1][:, :L]                        # u[:, j] = r[n-j]
    d = xf[:, F - 1 - Dfix]
    mc = lambda w: float(np.mean((d - u @ w) ** 2))
    J_mc_ex, J_mc_qs = mc(w_ex), mc(w_qs)
    w_hat = np.linalg.solve(u.T @ u / K, u.T @ d / K)
    J_hat = mc(w_hat)
    c1 = abs(J_mc_ex / J_ex - 1) < 0.02
    c2 = np.linalg.norm(w_hat - w_ex) / np.linalg.norm(w_ex) < 0.05
    differ = abs(J_mc_qs / J_mc_ex - 1)
    verdict("V7a oracle vs Monte-Carlo (S=1)", c1 and c2 and J_hat >= J_ex * 0.99,
            f"exact oracle J={J_ex:.5f}, Monte-Carlo MSE of the exact oracle filter={J_mc_ex:.5f} ({100*(J_mc_ex/J_ex-1):+.2f}%), best filter fitted from samples={J_hat:.5f}, "
            f"coefficient difference {100*np.linalg.norm(w_hat-w_ex)/np.linalg.norm(w_ex):.2f}%. "
            f"Quasi-static oracle filter would lose {100*differ:.2f}% in MSE here (J_qs formula={J_qs:.5f}).")
    # (b) measured MSE never below the oracle (pilot seed, primary channel, three rates)
    rows = []
    ok_b = True
    for S in (1000, 200, 50):
        exp = make_experiment(S, CFG["primary"], e, 1000)
        out = run_receivers(exp, Dfix, MU)
        n0, n1 = exp["N_T"], exp["n_total"]
        J3 = float(np.mean(out["e3"][n0:] ** 2)); J2 = float(np.mean(out["e2"][n0:] ** 2))
        Jo = oracle_mean(exp["taps"], n0, n1, L, Dfix, s2, stride=8)
        rows.append(dict(S=S, J_R2=J2, J_R3=J3, J_oracle=Jo))
        ok_b = ok_b and J3 >= Jo * 0.99 and J2 >= Jo * 0.99
        print(f"   S={S:5d}: J_oracle={Jo:.4f}  J_R3={J3:.4f} (excess {100*(J3/Jo-1):.0f}%)  J_R2={J2:.4f} (excess {100*(J2/Jo-1):.0f}%)   [pilot seed 1000, mu=2^-8, supervised]")
    LOG["V7b_rows"] = rows
    verdict("V7b measured MSE >= oracle", ok_b, "R2 and R3 MSE are not below the oracle MSE at any tested rate (one pilot seed; not a tracking result)")


if __name__ == "__main__":
    t0 = time.time()
    test_V0(); test_V1(); test_V2()
    Dfix = test_V5()
    LOG["Delta_fixed"] = Dfix
    test_V3(Dfix); test_V4(Dfix); test_V6(Dfix); test_V2b(Dfix); test_V7(Dfix)
    LOG["runtime_s"] = round(time.time() - t0, 1)
    json.dump(LOG, open("results/p1_results.json", "w"), indent=1, default=float)
    n_pass = sum(v["pass"] for v in LOG["tests"].values())
    print(f"\n{n_pass}/{len(LOG['tests'])} tests passed, runtime {LOG['runtime_s']} s")
