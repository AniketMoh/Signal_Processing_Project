"""E-6 check (L1 pilot-type, seeds 5500-5539): is the training adequate for all three P2 scenarios?
Training channels: c = 40 (large_up and mid_up start there) and c = 116 (the 'down' step starts there). mu = 2^-7 ... 2^-10 (the P2 grid), 16 and 14 dB.
(a) Mean-weight model (exact under the usual small-mu theory, starts from zero weights): remaining transient MSE at N_T,
    J_tr(N_T) = sum_i lambda_i (q_i . w_o)^2 (1 - mu lambda_i)^(2 N_T), compared with the static steady-state excess of LMS (J_ss - J_min).
    Acceptance (predeclared): J_tr <= 0.1 * (J_ss - J_min), i.e. the leftover start-up error is below 10 % of LMS's own noise.
(b) Measured: frozen-filter (R2) MSE on the training channel after training for N_T = 30000 and 60000, against a long-training reference
    (N_T = 200000, same seeds). Acceptance: difference not significant (95 % paired t-interval over seeds contains 0) and below 0.1*(J_ss - J_min).
Run from code/: python3 check_NT_p2.py"""
import json, numpy as np
from exp_lib import *
from misadj_lib import wiener
MUS = [2.0 ** -k for k in (7, 8, 9, 10)]; SEEDS = list(range(5500, 5540)); EVAL = 100000
out = {}
for snr in (16.0, 14.0):
    s2 = sigma_from_ebn0(snr) ** 2
    for c0 in (40, 116):
        h = np.array([1.0, c0 * DA, H2]); wo, Jmin, R = wiener(h, DELTA, s2); lam, Q = np.linalg.eigh(R); proj = (Q.T @ wo) ** 2
        print(f"\n{snr:.0f} dB, training channel c = {c0} (a = {c0*DA:.4f}): lambda_min {lam[0]:.4f}, J_min {Jmin:.5f}")
        print("   mu      tau=1/(2mu lmin)  J_tr(30000)/exc  J_tr(60000)/exc | R2 MSE: NT=30000  NT=60000  NT=200000 (ref) | diff 30k-ref [95% CI] / exc   diff 60k-ref [95% CI] / exc | verdict 30k / 60k")
        for mu in MUS:
            J2 = {}
            for NT in (30000, 60000, 200000):
                c = np.full(NT + EVAL, c0, dtype=np.int64); v = []
                for sd in SEEDS:
                    ex = make_exp_from_counter(c, NT, snr, sd); _, _, eA, eF, _ = run_lms(ex, mu, 10 ** 9)
                    v.append(np.mean(eF[NT:] ** 2))
                    if NT == 200000: J2.setdefault("ss3", []).append(np.mean(eA[NT:] ** 2))
                J2[NT] = np.array(v)
            exc = np.mean(J2["ss3"]) - Jmin                     # LMS steady-state excess on this channel (measured)
            jtr = {NT: float((lam * proj * (1 - mu * lam) ** (2 * NT)).sum()) for NT in (30000, 60000)}
            row = dict(tau=1 / (2 * mu * lam[0]), exc=exc, jtr=jtr)
            vs = []
            txt = []
            for NT in (30000, 60000):
                d = J2[NT] - J2[200000]; m = d.mean(); h95 = 2.02 * d.std(ddof=1) / np.sqrt(len(d))
                ok = (jtr[NT] <= 0.1 * exc) and (abs(m) <= 0.1 * exc or (m - h95 <= 0 <= m + h95))
                vs.append("PASS" if ok else "FAIL"); txt.append(f"{m/exc:+.3f} [{(m-h95)/exc:+.3f},{(m+h95)/exc:+.3f}]")
                row[f"diff_{NT}"] = (float(m), float(h95)); row[f"verdict_{NT}"] = vs[-1]
            print(f"   2^-{int(-np.log2(mu)):2d}   {row['tau']:10.0f}      {jtr[30000]/exc:12.2e}   {jtr[60000]/exc:12.2e}   |  {J2[30000].mean():.5f}   {J2[60000].mean():.5f}   {J2[200000].mean():.5f}        | {txt[0]:28s} {txt[1]:28s} | {vs[0]} / {vs[1]}")
            out[f"{snr:.0f}|{c0}|{mu}"] = row
json.dump(out, open("results/check_NT_p2.json", "w"), default=float)
