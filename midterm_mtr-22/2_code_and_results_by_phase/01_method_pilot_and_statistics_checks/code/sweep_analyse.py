"""Analysis of a sweep (final data and validation data), version 2 (20 Oct 2026, owner decisions E-1, E-3, A-1).
The earlier pilot version is kept unchanged as sweep_analyse_v1_pilot.py (it produced grid_pilot_analysis_*.json).

Metrics (unchanged definitions, PROJECT_SPEC Sec. 3):
  eps  = (J_R3 - J_or) / max(J_or, 1e-3)                J_or = window mean of the exact instantaneous-channel oracle MSE
  rho  = (eps - eps_static) / (eps_plateau - eps_static)
  eps_static (primary): occupancy-weighted MEASURED static LMS excess (linear interpolation over the static nodes);
  eps_static (sensitivity): the literal PPR-22 reading, static run at c_lo.
  MSE status: bootstrap over seeds of mean rho: P if upper < rho_th, F if lower > rho_th, else '?'.

BER criterion (S*_BER, PPR-22 Sec. 5.7, f = 2), primary method = PAIRED SEED-LEVEL BOOTSTRAP (E-1):
  - Each seed is one independent run.  The trajectory run and the static runs of the same seed share payload bits and noise
    (same seed), so one resample of seed indices is applied to BOTH (pairing kept).  Whole seeds are resampled, so the
    temporal dependence of errors inside a seed (bursts) is kept automatically.
  - Statistic: ratio = BER_R3(trajectory) / BER_ref, BER_ref = occupancy-weighted interpolation of the static node BERs.
    Interpolation (A-1): log-linear in c when every node has >= 1 observed error ('log'), otherwise linear ('lin');
    the linear value is always reported as a sensitivity column.  Log interpolation is a modelling assumption, not the true BER
    between nodes.  Inside a resample a node with zero errors is set to 0.5 errors (log method only).
  - Used only where the reference is resolved (owner rule, 20 Oct: OBSERVED counts): the observed static errors, weighted exactly as the
    nodes enter the reference (sum_j v_j K_j), are >= 100, AND the expected number of reference errors in the trajectory window
    (N_bits * BER_ref) is >= 100.  Status: P if the 97.5 % point of the ratio <= f,
    F if the 2.5 % point > f, '?' otherwise.  B = 2000 resamples.
  - Otherwise the point is REFERENCE-LIMITED: Wilson interval of R3 against f * BER_ref,UB (linear, 3/N for zero nodes):
    'p' (conditional pass), 'F' (rigorous fail) or '?'.
  - Sensitivity columns (not primary evidence): plain Wilson, burst-adjusted Wilson (gaps 10/20/40: mean burst size x Wilson on
    the number of bursts), both with the reference treated as exact; literal static-at-c_lo reference.
  S*_BER only if monotonicity is demonstrated (after the first non-pass, every faster point is 'F').

S_cross (E-3; PPR-22 Sec. 3.1): per S, paired bootstrap of d = BER_R3 - min(BER_R1, BER_R2) over seeds:
  'A' advantage demonstrated (97.5 % point < 0), 'L' loss of advantage CONFIRMED (2.5 % point > 0, R3 worse than the better control),
  '?' inconclusive.  Reported: the fastest S down to which the advantage is demonstrated, the first S (slow -> fast) without it
  and whether that is a confirmed loss or inconclusive; 'no S_cross observed within the grid' if every point is 'A'.
  The earlier one-sided z-test (assumes independent errors) is kept as a sensitivity string.
"""
import json, numpy as np
from exp_lib import *

TH = (0.25, 0.5, 0.75); FS = (1.5, 2.0, 5.0); B_BOOT = 2000; GAPS = (10, 20, 40)


# ------------------------------------------------------------------ small statistics helpers
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def burst_wilson(k, C, n):
    """Burst-adjusted Wilson: mean burst size x Wilson interval on the number of bursts (sensitivity only)."""
    if C == 0:
        return wilson(0, n)
    m = k / C
    l, u = wilson(C, n)
    return m * l, m * u


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


def parabola_min(x, y, k, npts=3):
    h = npts // 2
    if k - h < 0 or k + h >= len(x): return x[k]
    a, b, c = np.polyfit(x[k - h:k + h + 1], y[k - h:k + h + 1], 2)
    return (-b / (2 * a)) if a > 0 else x[k]


def resample_counts(ns, B, rng):
    """W[b, s] = how many times seed s is drawn in resample b (same W is used for trajectory and static runs = pairing)."""
    idx = rng.integers(0, ns, (B, ns))
    W = np.zeros((B, ns))
    np.add.at(W, (np.arange(B)[:, None], idx), 1.0)
    return W


def interp_matrix(cg, cs):
    """A[s, j]: linear-interpolation weight of node j for channel state cs[s]."""
    I = np.eye(len(cg))
    return np.column_stack([np.interp(cs, cg, I[j]) for j in range(len(cg))])


def ref_from_p(p, A, w, method):
    """Occupancy-weighted reference BER from node BERs p (shape (nodes,) or (B, nodes))."""
    if method == "log":
        return np.exp(np.log(p) @ A.T) @ w
    return (p @ A.T) @ w


def paired_ratio(E3, n_traj, K, n_node, A, w, method, W):
    """Paired seed-level bootstrap of BER_R3 / BER_ref.  E3: (ns,) R3 errors per seed; K: (nodes, ns) static errors per seed.
    Returns point ratio, 2.5 % and 97.5 % points, bootstrap standard deviation, and the reference point value."""
    ns = len(E3)
    b3 = E3.sum() / (ns * n_traj); pK = K.sum(axis=1) / (ns * n_node)
    ref = float(ref_from_p(pK, A, w, method))
    b3b = (W @ E3) / (ns * n_traj)
    pKb = (W @ K.T) / (ns * n_node)
    if method == "log":
        pKb = np.where(pKb > 0, pKb, 0.5 / (ns * n_node))
    rb = b3b / ref_from_p(pKb, A, w, method)
    return float(b3 / ref), float(np.percentile(rb, 2.5)), float(np.percentile(rb, 97.5)), float(rb.std(ddof=1)), ref


# ------------------------------------------------------------------ exponent of mu_opt(S) with its sensitivity (owner request)
def exponent_variants(eps_tab, rho_tab, S_list, mus):
    """eps_tab, rho_tab: arrays [S, mu] of seed-mean eps and rho.  Returns slope of log2 mu_opt against log2(1/S) for predeclared variants.
    The spread across variants is the systematic part of the uncertainty (the seed bootstrap only gives the statistical part)."""
    lm = np.log2(mus); out = {}
    def opt(i, npts):
        k = int(np.argmin(eps_tab[i])); br = 0 < k < len(mus) - 1
        return (parabola_min(lm, eps_tab[i], k, npts) if (br and npts > 1) else lm[k]), br, rho_tab[i, k]
    def fit(sel, npts):
        pts = [(S_list[i],) + opt(i, npts) for i in sel]
        pts = [p for p in pts if p[2]]                                   # bracketed optimum only
        if len(pts) < 4: return None, len(pts)
        x = np.log2([1.0 / p[0] for p in pts]); y = np.array([p[1] for p in pts])
        return float(np.polyfit(x, y, 1)[0]), len(pts)
    base = [i for i in range(len(S_list)) if opt(i, 3)[1] and opt(i, 3)[2] <= 0.75]
    out["V0 baseline (3-pt parabola, bracketed, rho<=0.75)"] = fit(base, 3)
    out["V1 no refinement (grid argmin)"] = fit(base, 1)
    out["V2 5-point quadratic refinement"] = fit(base, 5)
    out["V3 stricter range rho<=0.5"] = fit([i for i in base if opt(i, 3)[2] <= 0.5], 3)
    out["V4 drop the two slowest S"] = fit(base[2:], 3)
    out["V5 drop the two fastest S"] = fit(base[:-2], 3)
    out["V6 only S <= 1000"] = fit([i for i in base if S_list[i] <= 1000], 3)
    vals = [v[0] for v in out.values() if v[0] is not None]
    out["spread"] = (float(min(vals)), float(max(vals))) if vals else None
    return out


# ------------------------------------------------------------------ main analysis
def analyse(raw_path, cfg, snr, out_json=None, log=print, seed_boot=3):
    RAW = np.load(raw_path); lo, hi = cfg["channel"]; S_list = cfg["S_list"]; mus = cfg["mus"]; ns = len(cfg["seeds"])
    paired = bool(RAW["meta|paired"][0]) if "meta|paired" in RAW else (list(cfg["seeds"]) == list(cfg.get("static_seeds", cfg["seeds"])))
    s2 = sigma_from_ebn0(snr) ** 2; plat = plateau_stats(lo, hi, s2)["eps_plateau"]
    cg = np.array(cfg["static_c"]); cs = np.arange(lo, hi + 1); A = interp_matrix(cg, cs)
    Jmin_cg = np.array([Rp_const(c, s2)[1] for c in cg])
    Jss = np.array([RAW[f"{snr:.0f}|static_c{c}|J3"].mean(axis=1) for c in cg])               # [node, mu]
    Kseed = np.array([RAW[f"{snr:.0f}|static_c{c}|E3"] for c in cg]).astype(float)              # [node, mu, seed]
    n_node = float(RAW[f"{snr:.0f}|static_c{cg[0]}|bits"][0]) / Kseed.shape[2]                  # bits per seed per node
    rng = np.random.default_rng(seed_boot); W = resample_counts(ns, B_BOOT, rng)
    has_bursts = f"{snr:.0f}|{S_list[0]}|B3_20" in RAW
    res = {}
    log(f"\n######## Eb/N0 = {snr:.0f} dB  channel c {lo}..{hi}  eps_plateau = {plat:.3f}  seeds = {ns}  paired = {paired}  bursts stored = {has_bursts}")
    if not paired:
        log("  WARNING: static and trajectory seeds differ -> the 'paired' bootstrap is not paired here (resampling still by seed).")
    eps_tab = np.zeros((len(S_list), len(mus))); rho_tab = np.zeros_like(eps_tab)
    for i, mu in enumerate(mus):
        k0 = f"{snr:.0f}|None"; Jst = RAW[k0 + "|J3"][i]; Jor_st = RAW[k0 + "|Jor"][0]
        eps_lit = (Jst.mean() - Jor_st) / Jor_st
        N0 = ns * int(RAW[k0 + "|n_eval"][0]); k_lit = int(RAW[k0 + "|E3"][i].sum())
        K = Kseed[:, i, :]; pK = K.sum(axis=1) / (ns * n_node)
        method = "log" if np.all(pK > 0) else "lin"
        pK_ub = np.where(pK > 0, pK, 3.0 / (ns * n_node))
        rows = []
        for si, S in enumerate(S_list):
            key = f"{snr:.0f}|{S}"; J3 = RAW[key + "|J3"][i]; J2 = RAW[key + "|J2"][i]; Jor = RAW[key + "|Jor"][0]
            cw = RAW[key + "|c_win"].astype(int); n_traj = len(cw); NB = ns * n_traj
            w = np.bincount(cw - lo, minlength=hi - lo + 1) / n_traj                       # occupancy of every channel state
            eps_tr = float((w @ (A @ (Jss[:, i] - Jmin_cg))) / Jor)
            es = (J3 - Jor) / max(Jor, 1e-3)
            rl = (es - eps_lit) / (plat - eps_lit); rt = (es - eps_tr) / (plat - eps_tr)
            ml = (W @ rl) / ns; mt = (W @ rt) / ns
            eps_tab[si, i] = es.mean(); rho_tab[si, i] = rt.mean()
            E1s = RAW[key + "|E1"][i].astype(float); E2s = RAW[key + "|E2"][i].astype(float); E3s = RAW[key + "|E3"][i].astype(float)
            E1, E2, E3 = int(E1s.sum()), int(E2s.sum()), int(E3s.sum())
            ref_lin = float(ref_from_p(pK, A, w, "lin")); ref_log = float(ref_from_p(pK, A, w, "log")) if method == "log" else None
            ref_ub = float(ref_from_p(pK_ub, A, w, "lin")); ref_pt = ref_log if method == "log" else ref_lin
            v_node = w @ A                                                                   # weight of each static node in this reference
            K_obs = float(v_node @ K.sum(axis=1))                                             # OBSERVED static errors, weighted as in the reference
            enough = (K_obs >= 100) and (NB * ref_pt >= 100)                                  # owner rule (20 Oct): observed counts + expected trajectory count
            row = dict(S=S, N_eval=n_traj, N_bits=NB, Jor=float(Jor), J3=float(J3.mean()), J2=float(J2.mean()), eps3=float(es.mean()),
                       eps2=float(((J2 - Jor) / Jor).mean()), eps_st_traj=eps_tr, eps_st_lit=float(eps_lit),
                       rho_traj=(float(rt.mean()), float(np.percentile(mt, 2.5)), float(np.percentile(mt, 97.5))),
                       rho_lit=(float(rl.mean()), float(np.percentile(ml, 2.5)), float(np.percentile(ml, 97.5))),
                       E1=E1, E2=E2, E3=E3, ber1=E1 / NB, ber2=E2 / NB, ber3=E3 / NB, ref_method=method, ref_log=ref_log, ref_lin=ref_lin,
                       ref_ub=ref_ub, sufficient=bool(enough), exp_ref_err_traj=float(NB * ref_pt), obs_ref_err_static_weighted=K_obs,
                       obs_ref_err_static_total=int(K.sum()))
            if enough:
                row["ratio_boot"] = paired_ratio(E3s, n_traj, K, n_node, A, w, method, W)[:4]
                if method == "log":
                    row["ratio_boot_lin"] = paired_ratio(E3s, n_traj, K, n_node, A, w, "lin", W)[:4]
            if has_bursts:
                row["bursts"] = {g: int(RAW[key + f"|B3_{g}"][i].sum()) for g in GAPS}
            # S_cross: paired bootstrap of d = BER3 - min(BER1, BER2)
            b1 = (W @ E1s) / NB; b2 = (W @ E2s) / NB; b3 = (W @ E3s) / NB; d = b3 - np.minimum(b1, b2)
            ql, qh = np.percentile(d, [2.5, 97.5])
            row["cross"] = "A" if qh < 0 else ("L" if ql > 0 else "?")
            row["cross_z"] = "A" if (z_better(E3, E1, NB) and z_better(E3, E2, NB)) else "-"
            rows.append(row)
        # ---- statuses
        st = {}
        for th in TH:
            for nm in ("traj", "lit"):
                # rho is only defined when the plateau lies above the static baseline (eps_plateau > eps_static); otherwise the normalisation
                # has no room (the static LMS excess already exceeds the best fixed filter) and every status is 'x' (not defined)
                undefined = any((plat - (r["eps_st_traj"] if nm == "traj" else r["eps_st_lit"])) <= 0 for r in rows)
                if undefined:
                    st[f"{nm}_{th}"] = ("x" * len(rows), None, False, "rho undefined: static excess >= plateau (eps_static >= eps_plateau)", False)
                    continue
                sts = ["P" if r["rho_" + nm][2] < th else ("F" if r["rho_" + nm][1] > th else "?") for r in rows]
                st[f"{nm}_{th}"] = ("".join(sts),) + s_star(sts, S_list, strict=False) + (s_star(sts, S_list, strict=True)[1],)
        ber = {}
        for f in FS:
            prim, plain, lin_s = [], [], []; bw = {g: [] for g in GAPS}
            for r in rows:
                if r["sufficient"]:
                    lo_, hi_ = r["ratio_boot"][1], r["ratio_boot"][2]
                    prim.append("P" if hi_ <= f else ("F" if lo_ > f else "?"))
                    if "ratio_boot_lin" in r:
                        l2, h2 = r["ratio_boot_lin"][1], r["ratio_boot_lin"][2]; lin_s.append("P" if h2 <= f else ("F" if l2 > f else "?"))
                    else:
                        lin_s.append(prim[-1])
                    T = f * (r["ref_log"] if r["ref_method"] == "log" else r["ref_lin"])
                else:
                    T = f * r["ref_ub"]; l, u = wilson(r["E3"], r["N_bits"])
                    s = "P" if u <= T else ("F" if l > T else "?"); prim.append(s.lower() if s == "P" else s); lin_s.append(prim[-1])
                l, u = wilson(r["E3"], r["N_bits"]); s = "P" if u <= T else ("F" if l > T else "?")
                plain.append(s if r["sufficient"] else (s.lower() if s == "P" else s))
                if has_bursts:
                    for g in GAPS:
                        l, u = burst_wilson(r["E3"], r["bursts"][g], r["N_bits"]); s = "P" if u <= T else ("F" if l > T else "?")
                        bw[g].append(s if r["sufficient"] else (s.lower() if s == "P" else s))
            Sst = s_star(prim, S_list, strict=True)[0]
            if Sst is None:
                kind = None
            else:
                passes = prim[:S_list.index(Sst) + 1]
                kind = "resolved" if all(c == "P" for c in passes) else ("conditional (all passes reference-limited)" if all(c == "p" for c in passes)
                                                                        else "partly conditional (some passes reference-limited)")
            # descriptive only (does NOT replace the frozen strict rule): if no pass follows the first non-pass and the first non-pass points are
            # inconclusive '?' followed only by 'F', report the bracket [fastest pass, first rigorous fail] around the transition
            bracket = None
            fb_ = next((i for i, c_ in enumerate(prim) if c_ not in "Pp"), None)
            if Sst is None and fb_ is not None and fb_ > 0 and all(c_ not in "Pp" for c_ in prim[fb_:]):
                ff = next((i for i in range(fb_, len(prim)) if prim[i] == "F"), None)
                if ff is not None and all(c_ == "F" for c_ in prim[ff:]):
                    bracket = (S_list[fb_ - 1], S_list[ff])
            ber[f] = dict(primary="".join(prim), S_star=Sst, S_star_kind=kind, transition_bracket=bracket, mono=s_star(prim, S_list, strict=True)[1],
                          linear="".join(lin_s), S_star_linear=s_star(lin_s, S_list, strict=True)[0],
                          plain_wilson="".join(plain), S_star_plain=s_star(plain, S_list, strict=True)[0],
                          burst_wilson={g: "".join(v) for g, v in bw.items()} if has_bursts else None)
        blit = {}
        for f in FS:
            ref = (k_lit / N0) if k_lit > 0 else 3.0 / N0; sts = []
            for r in rows:
                l, u = wilson(r["E3"], r["N_bits"]); s = "P" if u <= f * ref else ("F" if l > f * ref else "?")
                sts.append(s.lower() if (s == "P" and k_lit == 0) else s)
            blit[f] = ("".join(sts),) + s_star(sts, S_list, strict=True)
        cr = "".join(r["cross"] for r in rows); first = next((j for j, c in enumerate(cr) if c != "A"), None)
        if first is None:
            cross = dict(text="no S_cross observed within the grid", S_adv_down_to=S_list[-1], S_first_without=None, kind=None)
        else:
            kind = "confirmed loss of advantage" if cr[first] == "L" else "inconclusive (advantage no longer demonstrated)"
            cross = dict(text=f"advantage demonstrated down to S = {S_list[first-1] if first > 0 else 'none'}; first S without it = {S_list[first]} ({kind})",
                         S_adv_down_to=(S_list[first - 1] if first > 0 else None), S_first_without=S_list[first], kind=kind)
        cross["status"] = cr; cross["z_test_sensitivity"] = "".join(r["cross_z"] for r in rows)
        res[str(mu)] = dict(rows=rows, mse=st, ber=ber, ber_lit=blit, cross=cross, eps_lit=float(eps_lit), k_lit=k_lit, N_lit=N0, ref_method=method)
        b2 = ber[2.0]
        log(f"\n  mu = 2^{np.log2(mu):.1f}:  static-reference interpolation {method}  (node errors: {int(K.sum())})")
        log("     S:                 " + " ".join(f"{r['S']:>5d}" for r in rows))
        log("     rho (traj):        " + " ".join(f"{r['rho_traj'][0]:5.2f}" for r in rows))
        log("     R3 BER:            " + " ".join(f"{r['ber3']:5.0e}" for r in rows))
        log("     ratio (paired bs): " + " ".join(f"{r['ratio_boot'][0]:5.2f}" if r["sufficient"] else "   rl" for r in rows))
        log(f"     MSE rho_th=.5 (traj): {st['traj_0.5'][0]}  S*_MSE {st['traj_0.5'][1]}   (.25/.75: {st['traj_0.25'][1]}/{st['traj_0.75'][1]}; literal: {st['lit_0.5'][1]})")
        log(f"     BER f=2 PRIMARY:      {b2['primary']}  S*_BER {b2['S_star']} [{b2['S_star_kind']}] (mono {b2['mono']}; bracket if not demonstrated: {b2['transition_bracket']});  f=1.5: {ber[1.5]['S_star']}  f=5: {ber[5.0]['S_star']}")
        log(f"       sens. linear:       {b2['linear']}  S* {b2['S_star_linear']}")
        log(f"       sens. plain Wilson: {b2['plain_wilson']}  S* {b2['S_star_plain']}")
        if has_bursts:
            log(f"       sens. burst Wilson: " + "  ".join(f"g{g}: {v}" for g, v in b2['burst_wilson'].items()))
        log(f"       sens. literal ref:  {blit[2.0][0]}  S* {blit[2.0][1]}")
        log(f"     S_cross: {cross['text']}   [status {cr}; z-test sens. {cross['z_test_sensitivity']}]")
    # ---- mu_opt and exponent (statistical bootstrap + systematic variants)
    lm = np.log2(mus); mopt = []
    for si, S in enumerate(S_list):
        e = eps_tab[si]; k = int(np.argmin(e)); br = 0 < k < len(mus) - 1
        mopt.append(dict(S=S, log2mu_refined=float(parabola_min(lm, e, k) if br else lm[k]), bracketed=bool(br), rho_at_opt=float(rho_tab[si, k])))
    var = exponent_variants(eps_tab, rho_tab, S_list, mus)
    stat_ci = None
    base_S = [m["S"] for m in mopt if m["bracketed"] and m["rho_at_opt"] <= 0.75]
    if len(base_S) >= 4:
        sl = []
        for b in range(400):
            ix = rng.integers(0, ns, ns); yy = []
            for S in base_S:
                key = f"{snr:.0f}|{S}"; Jor = RAW[key + "|Jor"][0]
                e = np.array([float(((RAW[key + "|J3"][j][ix] - Jor) / Jor).mean()) for j in range(len(mus))]); k = int(np.argmin(e))
                yy.append(parabola_min(lm, e, k) if 0 < k < len(mus) - 1 else lm[k])
            sl.append(np.polyfit(np.log2([1.0 / S for S in base_S]), yy, 1)[0])
        stat_ci = (float(np.percentile(sl, 2.5)), float(np.percentile(sl, 97.5)))
    log("\n  mu_opt(S): " + "  ".join(f"S={m['S']}: 2^{m['log2mu_refined']:.2f}{'' if m['bracketed'] else '*'}" for m in mopt))
    log("  exponent d log2 mu_opt / d log2(1/S):")
    for k_, v in var.items():
        if k_ != "spread": log(f"     {k_:50s} slope {v[0] if v[0] is None else round(v[0], 3)}  ({v[1]} points)")
    log(f"     statistical (seed bootstrap, baseline variant) 95% {stat_ci};  systematic spread across variants {var['spread']}")
    out = dict(snr=snr, channel=cfg["channel"], plateau=plat, res=res, mu_opt=mopt, exponent=dict(variants={k: v for k, v in var.items()}, stat_ci=stat_ci))
    if out_json: json.dump(out, open(out_json, "w"), default=float)
    return out
