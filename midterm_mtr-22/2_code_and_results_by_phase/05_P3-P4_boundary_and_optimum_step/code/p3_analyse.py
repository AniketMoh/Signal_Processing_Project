"""P3 pilot, analysis part (reads results/p3_raw.npz).  All numbers are L1 pilot results (seeds 1000-1019, supervised LMS).
eps_static baseline is reported under TWO readings because the spec says 'the static S0 run' without naming the channel value:
  lit  : static channel held at c_lo (literal S0 run)
  traj : average of the static (S -> infinity) excess over the channel values actually visited by the trajectory
Run: python3 p3_analyse.py > results/p3_analysis_log.txt"""
import json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from exp_lib import *
from p3_run import CHANNELS, SNRS, S_GRID, MUS, SEEDS, STATIC_SEEDS, N_T, N_EVAL

RAW = np.load("results/p3_raw.npz")
THS = (0.25, 0.5, 0.75); FS = (1.5, 2.0, 5.0); NB = len(SEEDS) * N_EVAL
OUT = {}
rng = np.random.default_rng(3)
BIDX = rng.integers(0, len(SEEDS), (1000, len(SEEDS)))


def ci_mean(v):
    m = v[BIDX].mean(axis=1)
    return float(v.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def status(lo, hi, th):
    return "P" if hi < th else ("F" if lo > th else "?")


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def s_star(sts):
    """sts: list of statuses from slow to fast.  Returns (S*, monotonic?, note)"""
    S = S_GRID
    first_bad = next((i for i, s in enumerate(sts) if s != "P"), None)
    if first_bad is None:
        return None, True, "no failure within the S grid"
    if first_bad == 0:
        return None, all(s != "P" for s in sts), "fails already at the slowest S" + ("" if all(s != "P" for s in sts) else " (but later points pass: not monotonic)")
    mono = all(s != "P" for s in sts[first_bad:])
    return (S[first_bad - 1] if mono else None), mono, ("" if mono else "not monotonic: passing set reported")


def z_better(k3, k_o, n):
    p3, po = k3 / n, k_o / n; p = (k3 + k_o) / (2 * n)
    if p == 0: return False
    z = (po - p3) / np.sqrt(2 * p * (1 - p) / n)
    return z > 1.645


def main():
    summary = {}
    for ch, (lo, hi) in CHANNELS.items():
        for snr in SNRS:
            s2 = sigma_from_ebn0(snr) ** 2
            pl = plateau_stats(lo, hi, s2); plat = pl["eps_plateau"]
            cg = RAW[f"{ch}|{snr:.0f}|cgrid"]
            Jmin_cg = np.array([Rp_const(c, s2)[1] for c in cg])
            Jss_cg = np.array([RAW[f"{ch}|{snr:.0f}|static_c{c}|J3"].mean(axis=1) for c in cg])        # [c, mu]
            # analytic checks of C2
            cs = np.arange(lo, hi + 1)
            cond = max(np.linalg.cond(Rp_const(c, s2)[2]) for c in cs)
            wgrid = np.linspace(0, np.pi, 2001)
            minH = min(abs(1 + c * DA * np.exp(-1j * wgrid) + H2 * np.exp(-2j * wgrid)).min() for c in (lo, hi))
            r1_hi = r1_exact_ber(hi * DA, H2, np.sqrt(s2))
            print(f"\n################ {ch}  c {lo}..{hi} (a {lo*DA:.3f}..{hi*DA:.3f})  Eb/N0 {snr:.0f} dB   eps_plateau (analytic, Delta=2) {plat:.3f}   eps_frozen(c_lo) {pl['eps_frozen_lo']:.2f}   cond(R) max {cond:.1f}   min|H| {minH:.3f}   R1 BER at a_hi (exact) {r1_hi:.2e}")
            per_mu = {}
            for i, mu in enumerate(MUS):
                key0 = f"{ch}|{snr:.0f}|None"
                Jst = RAW[key0 + "|J3"][i]; Jor_st = RAW[key0 + "|Jor"][0]
                eps_st_lit = (Jst.mean() - Jor_st) / Jor_st
                ber_st = RAW[key0 + "|E3"][i].sum() / NB
                rows = []
                for S in S_GRID:
                    key = f"{ch}|{snr:.0f}|{S}"
                    J3 = RAW[key + "|J3"][i]; J2 = RAW[key + "|J2"][i]; Jor = RAW[key + "|Jor"][0]; cwin = RAW[key + "|c_win"].astype(float)
                    exc = np.interp(cwin, cg, Jss_cg[:, i] - Jmin_cg)
                    eps_st_traj = float(exc.mean() / Jor)
                    eps_seed = (J3 - Jor) / max(Jor, 1e-3)
                    rl = (eps_seed - eps_st_lit) / (plat - eps_st_lit); rt = (eps_seed - eps_st_traj) / (plat - eps_st_traj)
                    m_l, lo_l, hi_l = ci_mean(rl); m_t, lo_t, hi_t = ci_mean(rt)
                    E1 = int(RAW[key + "|E1"][i].sum()); E2 = int(RAW[key + "|E2"][i].sum()); E3 = int(RAW[key + "|E3"][i].sum())
                    rows.append(dict(S=S, Jor=Jor, J3=float(J3.mean()), J2=float(J2.mean()), eps3=float(eps_seed.mean()), eps2=float(((J2 - Jor) / Jor).mean()),
                                     eps_st_lit=float(eps_st_lit), eps_st_traj=eps_st_traj, rho_lit=(m_l, lo_l, hi_l), rho_traj=(m_t, lo_t, hi_t),
                                     ber1=E1 / NB, ber2=E2 / NB, ber3=E3 / NB, E1=E1, E2=E2, E3=E3))
                st = {}
                for th in THS:
                    for nm in ("lit", "traj"):
                        sts = [status(r["rho_" + nm][1], r["rho_" + nm][2], th) for r in rows]
                        st[f"{nm}_{th}"] = ("".join(sts),) + s_star(sts)
                ref = max(ber_st, 3.0 / NB)
                bst = {}; bst_t = {}
                ber_cg = np.array([max(RAW[f"{ch}|{snr:.0f}|static_c{c}|E3"][i].sum() / NB, 3.0 / NB) for c in cg])   # static BER on the c grid (floor 3/N_bits)
                for r in rows:
                    cwin = RAW[f"{ch}|{snr:.0f}|{r['S']}|c_win"].astype(float)
                    r["ber_ref_traj"] = float(np.interp(cwin, cg, ber_cg).mean())
                for f in FS:
                    sts = []; sts_t = []
                    for r in rows:
                        l, u = wilson(r["E3"], NB)
                        sts.append("P" if u <= f * ref else ("F" if l > f * ref else "?"))
                        sts_t.append("P" if u <= f * r["ber_ref_traj"] else ("F" if l > f * r["ber_ref_traj"] else "?"))
                    bst[f] = ("".join(sts),) + s_star(sts); bst_t[f] = ("".join(sts_t),) + s_star(sts_t)
                cross = [r["S"] for r in rows if z_better(r["E3"], r["E1"], NB) and z_better(r["E3"], r["E2"], NB)]
                per_mu[mu] = dict(rows=rows, eps_st_lit=float(eps_st_lit), ber_static=ber_st, mse_status=st, ber_status={str(k): v for k, v in bst.items()}, ber_status_traj={str(k): v for k, v in bst_t.items()}, S_cross_set=cross)
                print(f"  mu=2^-{int(-np.log2(mu)):2d}: eps_static lit {100*eps_st_lit:5.1f}% / traj(S=1000) {100*rows[0]['eps_st_traj']:5.1f}%  R3 static BER {ber_st:.1e} (ref {ref:.1e})")
                print(f"      S:                {' '.join(f'{S:>5d}' for S in S_GRID)}")
                print(f"      eps_R3 (%):       {' '.join(f'{100*r['eps3']:5.0f}' for r in rows)}")
                print(f"      rho (lit)  mean:  {' '.join(f'{r['rho_lit'][0]:5.2f}' for r in rows)}")
                print(f"      rho (traj) mean:  {' '.join(f'{r['rho_traj'][0]:5.2f}' for r in rows)}")
                print(f"      MSE status th=.5 lit/traj: {st['lit_0.5'][0]} / {st['traj_0.5'][0]}   S*_MSE lit {st['lit_0.5'][1]} traj {st['traj_0.5'][1]}   (th .25: {st['lit_0.25'][1]}/{st['traj_0.25'][1]}; th .75: {st['lit_0.75'][1]}/{st['traj_0.75'][1]})  monotonic lit/traj {st['lit_0.5'][2]}/{st['traj_0.5'][2]}")
                print(f"      BER R1:           {' '.join(f'{r['ber1']:5.0e}' for r in rows)}")
                print(f"      BER R2:           {' '.join(f'{r['ber2']:5.0e}' for r in rows)}")
                print(f"      BER R3:           {' '.join(f'{r['ber3']:5.0e}' for r in rows)}")
                print(f"      static-BER reference along the trajectory (traj): {' '.join(f'{r['ber_ref_traj']:5.0e}' for r in rows)}")
                print(f"      BER status f=2 (traj baseline): {bst_t[2.0][0]}  S*_BER {bst_t[2.0][1]} (f=1.5: {bst_t[1.5][1]}, f=5: {bst_t[5.0][1]}) {bst_t[2.0][3]}")
                print(f"      BER status f=2 (literal S0 at c_lo): {bst[2.0][0]}  S*_BER {bst[2.0][1]} (f=1.5: {bst[1.5][1]}, f=5: {bst[5.0][1]})   S_cross set (smallest S with significant R3 advantage over both): {min(cross) if cross else 'none'}")
            # mu_opt (eps_R3 over mu, per S) -- preview only
            mo = []
            for si, S in enumerate(S_GRID):
                e = np.array([per_mu[mu]["rows"][si]["eps3"] for mu in MUS]); k = int(np.argmin(e))
                lm = np.log2(MUS)
                if 0 < k < len(MUS) - 1:
                    a, b, c_ = np.polyfit(lm[k - 1:k + 2], e[k - 1:k + 2], 2); mopt = 2 ** (-b / (2 * a)) if a > 0 else MUS[k]
                else:
                    mopt = MUS[k]
                mo.append((S, MUS[k], float(mopt), k in (0, len(MUS) - 1)))
            print("  mu_opt(S) preview (grid argmin of eps_R3, parabolic refinement; * = at grid boundary):  " + "  ".join(f"S={S}: 2^{np.log2(m):.1f}{'*' if bd else ''}" for S, g, m, bd in mo))
            # C-criteria
            c1 = plat >= 1.0; c2 = cond <= 70 and minH >= 0.15
            ber_ref = max(per_mu[MUS[2]]["ber_static"], 3.0 / NB)
            c3a = r1_hi >= 10 * ber_ref
            c3b = max(r["ber2"] for r in per_mu[MUS[2]]["rows"]) * 1e7 >= 100
            def c4(nm):
                good = []
                for mu in MUS:
                    sts = per_mu[mu]["mse_status"][f"{nm}_0.5"][0]
                    npass = sts.count("P"); nfail = sts.count("F")
                    mono = per_mu[mu]["mse_status"][f"{nm}_0.5"][2]
                    if npass >= 2 and nfail >= 2 and mono: good.append(f"2^{int(np.log2(mu))}")
                return good
            summary[f"{ch}|{snr:.0f}"] = dict(C1=bool(c1), C2=bool(c2), C3a=bool(c3a), C3b=bool(c3b), C4_lit=c4("lit"), C4_traj=c4("traj"), eps_plateau=plat, cond=float(cond), minH=float(minH), r1_hi=float(r1_hi))
            s = summary[f"{ch}|{snr:.0f}"]
            print(f"  >>> selection criteria: C1 {c1} (plateau {plat:.2f})  C2 {c2}  C3a {c3a} (R1 {r1_hi:.1e} vs 10x R3-static-ref {10*ber_ref:.1e})  C3b {c3b}  C4 (MSE, rho_th=.5) lit: {s['C4_lit']}  traj: {s['C4_traj']}")
            OUT[f"{ch}|{snr:.0f}"] = {str(mu): per_mu[mu] for mu in MUS}
            # figures data
            OUT[f"{ch}|{snr:.0f}|mu_opt"] = mo
    print("\n==== SUMMARY OF SELECTION CRITERIA (pilot, L1) ====")
    for k, v in summary.items():
        print(f"  {k:18s} C1 {str(v['C1']):5s} C2 {str(v['C2']):5s} C3a {str(v['C3a']):5s} C3b {str(v['C3b']):5s} C4(lit) {v['C4_lit']}  C4(traj) {v['C4_traj']}")
    # figures
    for nm, fn in (("rho", "fig_P3_rho_vs_S.png"), ("ber", "fig_P3_ber_vs_S.png"), ("eps", "fig_P3_eps_vs_S.png")):
        fig, ax = plt.subplots(2, 3, figsize=(16, 8))
        for a_i, snr in enumerate(SNRS):
            for c_i, ch in enumerate(CHANNELS):
                A = ax[a_i, c_i]; d = OUT[f"{ch}|{snr:.0f}"]
                if nm == "rho":
                    for mu in MUS:
                        rr = d[str(mu)]["rows"]
                        A.errorbar(S_GRID, [r["rho_traj"][0] for r in rr], yerr=[[r["rho_traj"][0] - r["rho_traj"][1] for r in rr], [r["rho_traj"][2] - r["rho_traj"][0] for r in rr]], marker="o", ms=3, lw=1, label=f"2^-{int(-np.log2(mu))}")
                    for th in THS: A.axhline(th, color="gray", ls=":", lw=.7)
                    A.set_ylabel("rho (traj baseline)")
                elif nm == "ber":
                    d8 = d[str(MUS[2])]["rows"]; d10 = d[str(MUS[4])]["rows"]
                    A.plot(S_GRID, [max(r["ber1"], 1e-7) for r in d8], "k-o", ms=3, label="R1")
                    A.plot(S_GRID, [max(r["ber2"], 1e-7) for r in d8], "r-o", ms=3, label="R2 frozen")
                    A.plot(S_GRID, [max(r["ber3"], 1e-7) for r in d8], "-o", ms=3, label="R3 mu=2^-8")
                    A.plot(S_GRID, [max(r["ber3"], 1e-7) for r in d10], "--o", ms=3, label="R3 mu=2^-10")
                    A.set_yscale("log"); A.set_ylabel("BER (pooled, floor 1e-7 on plot)")
                else:
                    for mu in MUS:
                        rr = d[str(mu)]["rows"]; A.plot(S_GRID, [r["eps3"] for r in rr], "-o", ms=3, label=f"R3 2^-{int(-np.log2(mu))}")
                    A.plot(S_GRID, [d[str(MUS[2])]["rows"][j]["eps2"] for j in range(len(S_GRID))], "k--", label="R2 frozen")
                    A.axhline(summary[f"{ch}|{snr:.0f}"]["eps_plateau"], color="gray", ls=":"); A.set_yscale("log"); A.set_ylabel("eps = (J - J_or)/J_or")
                A.set_xscale("log"); A.invert_xaxis(); A.set_xlabel("S (symbols per coefficient step; slow to fast)"); A.set_title(f"{ch}, {snr:.0f} dB", fontsize=9); A.legend(fontsize=6)
        fig.tight_layout(); fig.savefig("results/" + fn, dpi=110); plt.close(fig)
    json.dump(dict(summary=summary, data=OUT), open("results/p3_results.json", "w"), default=float)


if __name__ == "__main__":
    main()
