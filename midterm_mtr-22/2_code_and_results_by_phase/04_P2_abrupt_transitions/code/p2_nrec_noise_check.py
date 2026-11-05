"""Check: is the measured N_rec (last time the 64-symbol moving average of the 100-seed mean MSE is above (1+kappa) J_ss) biased
upward by noise?  Take the noise-free model curve J_ss + transient(k), multiply every sample by chi-square(100)/100 (the noise of a mean
of 100 squared Gaussian errors), apply the same N_rec rule 300 times.  Compares noise-free N_rec with the mean noisy N_rec."""
import json, numpy as np
from exp_lib import *
from p2_abrupt import moving_avg, n_rec_from, STEPS, MUS, N_C, N_POST, W, KAPPA, S2
res = json.load(open("results/p2_results.json"))
out = {}
rng = np.random.default_rng(11)


def noise_factor(c, mu=2.0 ** -8):
    """var(64-symbol MA of e^2) / (2 J^2 / 64), measured on a static channel (4 seeds x 400000)."""
    v = []
    for seed in range(1000, 1004):
        ex = make_exp_from_counter(np.full(400000, c, dtype=np.int64), 30000, 14.0, seed)
        _, _, eA, _, _ = run_lms(ex, mu, 10 ** 9)
        e2 = eA[50000:] ** 2
        v.append(np.var(moving_avg(e2, 64)[::64]))
    return float(np.mean(v) / (2 * np.mean(e2) ** 2 / 64))


FACT = {c: noise_factor(c) for c in (40, 77, 116)}
print("measured noise factors (var of MA64 of e^2 over iid value):", {c: round(f, 2) for c, f in FACT.items()})
print("step, mu: measured N_rec | noise-free model N_rec | model + noise (mean, 2.5-97.5 %) ")
for sname, (cA, cB) in STEPS.items():
    wA, JA, RA, pA = Rp_const(cA, S2); wB, JB, RB, pB = Rp_const(cB, S2)
    lam, Q = np.linalg.eigh(RB); coef = Q.T @ (wA - wB)
    for mu in MUS:
        r = res["steps"][sname][str(mu)]
        Jss = r["Jss_B"]; thr = (1 + KAPPA) * Jss
        kk = np.arange(N_POST)
        trans = (lam[:, None] * coef[:, None] ** 2 * (1 - mu * lam[:, None]) ** (2 * kk[None, :])).sum(axis=0)
        # series on the same index as p2: n = N_C-(W-1) ... ; first W-1 entries (before N_C) at the pre level -> use the post model shifted by L-1 and a frozen-level plateau
        Jfr = JB + trans[0]
        base = np.concatenate([np.full(W - 1 + 15, Jfr), Jss + trans[: N_POST - 15]])
        base = base[: N_POST + W - 1]
        n0 = n_rec_from(base, thr)
        fac = np.sqrt(FACT[cB])
        noisy = np.array([n_rec_from(base * (1 + fac * (rng.chisquare(100, base.shape) / 100.0 - 1)), thr) for _ in range(300)])
        ok = np.isfinite(noisy)
        out[f"{sname}|{mu}"] = dict(measured=r["N_rec"], noise_free=n0, noisy_mean=float(np.nanmean(noisy)), noisy_lo=float(np.nanpercentile(noisy, 2.5)), noisy_hi=float(np.nanpercentile(noisy, 97.5)))
        print(f"  {sname[:8]:8s} mu=2^-{int(-np.log2(mu)):2d}: {r['N_rec']:7.0f} | {n0:7.0f} | {np.nanmean(noisy):7.0f} ({np.nanpercentile(noisy,2.5):.0f}-{np.nanpercentile(noisy,97.5):.0f})")
json.dump(out, open("results/p2_nrec_noise_check.json", "w"), indent=1)
