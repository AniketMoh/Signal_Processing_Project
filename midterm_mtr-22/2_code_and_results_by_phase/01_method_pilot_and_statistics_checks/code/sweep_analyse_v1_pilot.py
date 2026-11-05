"""Analysis of a sweep (pilot grid now, final data later) with the conventions of approved P-10 / P-12 (with the owner's clarifications, 20 Oct).
Metrics (all normalised exactly as in PROJECT_SPEC Sec. 3):
  eps      = (J_R3 - J_or) / max(J_or, 1e-3)         J_or = window-mean exact instantaneous-channel oracle MSE
  rho      = (eps - eps_static) / (eps_plateau - eps_static),  eps_plateau analytic quasi-static (best fixed filter for the averaged channel)
  eps_static (PRIMARY, trajectory-averaged): [ sum_n ( J_static(c(n),mu) - J_min(c(n)) ) / N_eval ] / J_or ; J_static = MEASURED steady-state R3 MSE of LMS on a static channel
              (linear interpolation in c over the static grid, weights = occupancy of c(n) in the window); the oracle enters only through the denominators and J_min.
  eps_static (SENSITIVITY, literal PPR-22 reading): the same on the static S0 run held at c_lo.
  MSE status: pass if bootstrap-95% upper limit of mean rho < rho_th, fail if lower limit > rho_th, else indeterminate (counted as not passing).
  BER: pooled R3 errors k of N_bits; Wilson 95% interval; threshold T = f * BER_ref.
       BER_ref,obs = occupancy-weighted mean of the OBSERVED static BERs (zero counts stay zero);  BER_ref,UB = same with 3/N_static (rule of three) ONLY for static grid values with zero errors.
       The reference is RESOLVED if N_bits * BER_ref,obs >= 100 (expected reference errors in the run); then T = f*BER_ref,obs.  Otherwise it is REFERENCE-LIMITED: T = f*BER_ref,UB,
       and a pass is labelled 'p' (proves only R3 <= T, a conservative-looking pass), a fail 'F' stays rigorous (T >= f * true reference with ~95% confidence).
       pass 'P'/'p': Wilson upper <= T; fail 'F': Wilson lower > T; otherwise '?' (inconclusive).
  S*_BER reported only if monotonicity is DEMONSTRATED: after the first failing grid point every faster point also fails ('F'); otherwise the status string is reported and S*_BER is undefined.
  S_cross: smallest S with R3 BER significantly lower than both R1 and R2 (one-sided two-proportion z-test, 5 %); 'no S_cross observed within the grid' if that holds at every grid point.
"""
import json, numpy as np
from exp_lib import *

TH = (0.25, 0.5, 0.75); FS = (1.5, 2.0, 5.0)


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def z_better(k3, ko, n):
    p = (k3 + ko) / (2 * n)
    if p == 0: return False
    return (ko / n - k3 / n) / np.sqrt(2 * p * (1 - p) / n) > 1.645


def s_star(sts, S_list, strict):
    """sts: statuses slow -> fast.  Returns (S*, monotonic, note).  S* = fastest S before the first non-pass."""
    ok = lambda s: s in ("P", "p")
    fb = next((i for i, s in enumerate(sts) if not ok(s)), None)
    if fb is None: return None, True, "no failure within the grid"
    if fb == 0: return None, all(not ok(s) for s in sts), "fails at the slowest S"
    later = sts[fb:]
    mono = all(s == "F" for s in later) if strict else all(not ok(s) for s in later)
    return (S_list[fb - 1] if mono else None), mono, ("" if mono else "monotonicity not demonstrated")


def parabola_min(x, y, k):
    a, b, c = np.polyfit(x[k - 1:k + 2], y[k - 1:k + 2], 2)
    return (-b / (2 * a)) if a > 0 else x[k]


def analyse(raw_path, cfg, snr, out_json=None, boot=1000, log=print):
    RAW = np.load(raw_path); lo, hi = cfg["channel"]; S_list = cfg["S_list"]; mus = cfg["mus"]; ns = len(cfg["seeds"])
    s2 = sigma_from_ebn0(snr) ** 2; plat = plateau_stats(lo, hi, s2)["eps_plateau"]
    cg = np.array(cfg["static_c"]); Jmin_cg = np.array([Rp_const(c, s2)[1] for c in cg])
    Jss = np.array([RAW[f"{snr:.0f}|static_c{c}|J3"].mean(axis=1) for c in cg])
    Kc = np.array([RAW[f"{snr:.0f}|static_c{c}|E3"].sum(axis=1) for c in cg]).astype(float)
    Nc = np.array([float(RAW[f"{snr:.0f}|static_c{c}|bits"][0]) for c in cg])[:, None]
    p_obs = Kc / Nc; p_ub = np.where(Kc > 0, Kc / Nc, 3.0 / Nc)
    rng = np.random.default_rng(3); BI = rng.integers(0, ns, (boot, ns))
    res = {}
    log(f"\n######## Eb/N0 = {snr:.0f} dB   primary channel c {lo}..{hi}   eps_plateau = {plat:.3f}   seeds = {ns}")
    for i, mu in enumerate(mus):
        k0 = f"{snr:.0f}|None"; Jst = RAW[k0 + "|J3"][i]; Jor_st = RAW[k0 + "|Jor"][0]
        eps_lit = (Jst.mean() - Jor_st) / Jor_st
        N0 = ns * int(RAW[k0 + "|n_eval"][0]); k_lit = int(RAW[k0 + "|E3"][i].sum())
        rows = []
        for S in S_list:
            key = f"{snr:.0f}|{S}"; J3 = RAW[key + "|J3"][i]; J2 = RAW[key + "|J2"][i]; Jor = RAW[key + "|Jor"][0]
            cw = RAW[key + "|c_win"].astype(float); NB = ns * len(cw)
            eps_tr = float(np.interp(cw, cg, Jss[:, i] - Jmin_cg).mean() / Jor)
            es = (J3 - Jor) / max(Jor, 1e-3)
            rl = (es - eps_lit) / (plat - eps_lit); rt = (es - eps_tr) / (plat - eps_tr)
            ml = rl[BI].mean(axis=1); mt = rt[BI].mean(axis=1)
            E1 = int(RAW[key + "|E1"][i].sum()); E2 = int(RAW[key + "|E2"][i].sum()); E3 = int(RAW[key + "|E3"][i].sum())
            ref_obs = float(np.interp(cw, cg, p_obs[:, i]).mean()); ref_ub = float(np.interp(cw, cg, p_ub[:, i]).mean())
            resolved = NB * ref_obs >= 100
            rows.append(dict(S=S, N_eval=len(cw), N_bits=NB, Jor=float(Jor), J3=float(J3.mean()), J2=float(J2.mean()), eps3=float(es.mean()), eps2=float(((J2 - Jor) / Jor).mean()),
                             eps_st_traj=eps_tr, eps_st_lit=float(eps_lit),
                             rho_traj=(float(rt.mean()), float(np.percentile(mt, 2.5)), float(np.percentile(mt, 97.5))),
                             rho_lit=(float(rl.mean()), float(np.percentile(ml, 2.5)), float(np.percentile(ml, 97.5))),
                             E1=E1, E2=E2, E3=E3, ber3=E3 / NB, ber1=E1 / NB, ber2=E2 / NB, ref_obs=ref_obs, ref_ub=ref_ub, resolved=bool(resolved)))
        st = {}
        for th in TH:
            for nm in ("traj", "lit"):
                sts = ["P" if r["rho_" + nm][2] < th else ("F" if r["rho_" + nm][1] > th else "?") for r in rows]
                st[f"{nm}_{th}"] = ("".join(sts),) + s_star(sts, S_list, strict=False) + (s_star(sts, S_list, strict=True)[1],)
        bst = {}
        for f in FS:
            sts = []
            for r in rows:
                T = f * (r["ref_obs"] if r["resolved"] else r["ref_ub"]); l, u = wilson(r["E3"], r["N_bits"])
                s = "P" if u <= T else ("F" if l > T else "?")
                sts.append(s.lower() if (s == "P" and not r["resolved"]) else s)
            bst[f] = ("".join(sts),) + s_star(sts, S_list, strict=True)
        blit = {}
        for f in FS:
            ref = (k_lit / N0) if k_lit > 0 else 3.0 / N0
            sts = []
            for r in rows:
                l, u = wilson(r["E3"], r["N_bits"]); s = "P" if u <= f * ref else ("F" if l > f * ref else "?")
                sts.append(s.lower() if (s == "P" and k_lit == 0) else s)
            blit[f] = ("".join(sts),) + s_star(sts, S_list, strict=True)
        cross = [r["S"] for r in rows if z_better(r["E3"], r["E1"], r["N_bits"]) and z_better(r["E3"], r["E2"], r["N_bits"])]
        res[str(mu)] = dict(rows=rows, mse=st, ber=bst, ber_lit=blit, S_cross_all=len(cross) == len(rows), S_cross_min=min(cross) if cross else None, eps_lit=float(eps_lit), k_lit=k_lit, N_lit=N0)
        log(f"\n  mu = 2^{np.log2(mu):.1f}:  eps_static literal {100*eps_lit:5.1f}%   static S0 R3 errors {k_lit} of {N0:.1e}")
        log("     S:             " + " ".join(f"{r['S']:>6d}" for r in rows))
        log("     eps3 (%):      " + " ".join(f"{100*r['eps3']:6.0f}" for r in rows))
        log("     rho (traj):    " + " ".join(f"{r['rho_traj'][0]:6.2f}" for r in rows))
        log("     R3 BER:        " + " ".join(f"{r['ber3']:6.0e}" for r in rows))
        log("     ref (obs|UB):  " + f"obs {rows[0]['ref_obs']:.1e} / UB {rows[0]['ref_ub']:.1e} at S=slowest; resolved at slowest S: {rows[0]['resolved']} (expected ref errors {rows[0]['N_bits']*rows[0]['ref_obs']:.0f})")
        log(f"     MSE rho_th=.5 traj: {st['traj_0.5'][0]}  S*_MSE {st['traj_0.5'][1]}   (rho_th .25 / .75: {st['traj_0.25'][1]} / {st['traj_0.75'][1]}; literal baseline at .5: {st['lit_0.5'][1]})")
        log(f"     BER f=2 (traj, P-10): {bst[2.0][0]}  S*_BER {bst[2.0][1]}  mono_demonstrated {bst[2.0][2]}   (f=1.5: {bst[1.5][1]}, f=5: {bst[5.0][1]});  literal-S0 reference: {blit[2.0][0]} S*_BER {blit[2.0][1]}")
        log(f"     S_cross: {'no S_cross observed within the grid' if res[str(mu)]['S_cross_all'] else 'smallest S with significant advantage = ' + str(res[str(mu)]['S_cross_min'])}")
    # mu_opt and exponent
    lm = np.log2(mus); mopt = []
    for si, S in enumerate(S_list):
        e = np.array([res[str(m)]["rows"][si]["eps3"] for m in mus]); k = int(np.argmin(e))
        br = 0 < k < len(mus) - 1
        lo_ = parabola_min(lm, e, k) if br else lm[k]
        rho_opt = res[str(mus[k])]["rows"][si]["rho_traj"][0]
        mopt.append(dict(S=S, k=k, mu_grid=float(mus[k]), log2mu_refined=float(lo_), bracketed=bool(br), rho_at_opt=float(rho_opt)))
    use = [m for m in mopt if m["bracketed"] and m["rho_at_opt"] <= 0.75]
    log("\n  mu_opt(S): " + "  ".join(f"S={m['S']}: 2^{m['log2mu_refined']:.2f}{'' if m['bracketed'] else '*'}" for m in mopt) + "   (* = optimum at the grid boundary)")
    exp = None
    if len(use) >= 4:
        x = np.log2([1.0 / m["S"] for m in use]); y = np.array([m["log2mu_refined"] for m in use]); A = np.polyfit(x, y, 1)
        sl = []
        for b in range(400):
            ix = rng.integers(0, ns, ns); yy = []
            for m in use:
                si = S_list.index(m["S"]); e = []
                for mu in mus:
                    key = f"{snr:.0f}|{m['S']}"; J3 = RAW[key + "|J3"][mus.index(mu)][ix]; Jor = RAW[key + "|Jor"][0]
                    e.append(float(((J3 - Jor) / Jor).mean()))
                e = np.array(e); k = int(np.argmin(e)); yy.append(parabola_min(lm, e, k) if 0 < k < len(mus) - 1 else lm[k])
            sl.append(np.polyfit(x, np.array(yy), 1)[0])
        exp = dict(slope=float(A[0]), ci=(float(np.percentile(sl, 2.5)), float(np.percentile(sl, 97.5))), n_points=len(use), S_used=[m["S"] for m in use])
        log(f"  exponent preview: d log2 mu_opt / d log2 (1/S) = {A[0]:.2f}  bootstrap 95% [{exp['ci'][0]:.2f}, {exp['ci'][1]:.2f}]  using S = {exp['S_used']} (bracketed, rho at optimum <= 0.75)")
    else:
        log(f"  exponent: only {len(use)} usable S points (need >= 4)")
    out = dict(snr=snr, plateau=plat, res=res, mu_opt=mopt, exponent=exp)
    if out_json: json.dump(out, open(out_json, "w"), default=float)
    return out
