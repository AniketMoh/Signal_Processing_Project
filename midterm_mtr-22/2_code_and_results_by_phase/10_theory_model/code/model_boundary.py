"""model_boundary.py -- a THEORY model of the tracking boundary and of the optimum step size, with no LMS simulation and no fitted constant.
Level: analytic / deterministic computation (it predicts L1 results; it is compared with the final L1 measurements).

Model (first order in mu, independence assumption, the same assumptions as PPR-22 Eq. (9)):
  excess MSE of R3 = LAG part + GRADIENT-NOISE part
  * LAG: the MEAN weight follows the deterministic recursion  wbar[n+1] = wbar[n] + mu*(p[n] - R[n] wbar[n]),  started from the Wiener
    filter of the training channel.  R[n], p[n] are the EXACT moving-window statistics of the channel (row j of the channel matrix uses
    the taps active at n-j), the same ones the oracle uses.  Lag excess at time n = J_n(wbar[n]) - J_or[n].  Averaged over the same
    evaluation window as the measurement and divided by the same mean oracle MSE -> eps_lag(mu, S).
  * GRADIENT NOISE: for each channel state c, the first-order excess of the correlated-error model already derived in P1
    (misadj_lib.exact_C / first_order_excess, finding F-1), averaged over the time the trajectory spends at each c -> eps_gn(mu).
  Predictions:  eps3 = eps_lag + eps_gn ;  rho = eps_lag / (eps_plateau - eps_gn) ;  S*_MSE = last S (slow -> fast) with rho < 0.5 ;
                mu_opt(S) = argmin over mu of eps3.
  A semi-empirical variant replaces eps_gn by the MEASURED trajectory-averaged static excess (isolates the lag model).
usage: python3 model_boundary.py      outputs results/model/*.json, *_log.txt, figures."""
import os, json, numpy as np
from numba import njit
from config import CFG, DA, sigma_from_ebn0
from lms_lib import triangle_counter
from exp_lib import Rp_const
from misadj_lib import exact_C, first_order_excess
OUT = "results/model"; os.makedirs(OUT, exist_ok=True)
L, M, H2, NT, DELTA = CFG["L"], 3, CFG["h2"], CFG["N_T"], 2


@njit(cache=True)
def lag_excess(a, n0, n1, mu, s2, w0, L, Delta):
    """Mean-weight recursion over n0..n1-1 for the channel [1, a[n], H2]; returns the mean of J_n(wbar[n]) (a-priori, before the update)."""
    w = w0.copy(); z = np.zeros(L + 2); p = np.zeros(L); Rw = np.zeros(L); tot = 0.0
    for n in range(n0, n1):
        # z = H^T w  (H[j, j+k] = taps at time n-j)
        for m in range(L + 2):
            z[m] = 0.0
        for j in range(L):
            t1 = a[n - j]
            z[j] += w[j]; z[j + 1] += t1 * w[j]; z[j + 2] += 0.1 * w[j]
        Jw = 1.0
        for j in range(L):
            # p[j] = H[j, Delta] = tap (Delta - j) at time n-j
            k = Delta - j
            if k == 0: p[j] = 1.0
            elif k == 1: p[j] = a[n - j]
            elif k == 2: p[j] = 0.1
            else: p[j] = 0.0
            Rw[j] = z[j] + a[n - j] * z[j + 1] + 0.1 * z[j + 2] + s2 * w[j]
            Jw += -2.0 * w[j] * p[j] + s2 * w[j] * w[j]
        for m in range(L + 2):
            Jw += z[m] * z[m]
        tot += Jw
        for j in range(L):
            w[j] += mu * (p[j] - Rw[j])
    return tot / (n1 - n0)


def gn_per_state(c_lo, c_hi, s2):
    """first-order gradient-noise excess per unit mu, for every counter value (correlated-error model of P1)."""
    out = {}
    for c in range(c_lo, c_hi + 1):
        h = [1.0, c * DA, H2]
        w, J, R, p = Rp_const(c, s2)
        out[c] = first_order_excess(1.0, exact_C(h, w, DELTA, s2))
    return out


def analyse(tag):
    A = json.load(open(f"results/final/analysis_{tag}.json"))
    lo, hi = (40, 116) if tag.startswith("primary") else (26, 77)
    snr = A["snr"]; s2 = sigma_from_ebn0(snr) ** 2; plat = A["plateau"]
    mus = sorted(float(m) for m in A["res"]); rows0 = A["res"][str(mus[0]) if str(mus[0]) in A["res"] else list(A["res"])[0]]["rows"]
    Ss = [r["S"] for r in rows0]
    gn1 = gn_per_state(lo, hi, s2)
    w0 = Rp_const(lo, s2)[0]
    log = open(f"{OUT}/{tag}_log.txt", "w")
    def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()
    lg(f"=== {tag}: {snr} dB, channel {lo}-{hi}, plateau {plat:.3f} ===")
    traj = {}
    for S in Ss:
        ne = [r["N_eval"] for r in rows0 if r["S"] == S][0]
        c = triangle_counter(NT + ne, NT, lo, hi, S)
        wts = np.bincount(c[NT:] - lo, minlength=hi - lo + 1) / ne
        traj[S] = (c * DA, ne, float(sum(wts[i] * gn1[lo + i] for i in range(hi - lo + 1))))
    pred = {}; cmp_rows = []
    for mu in mus:
        R = {r["S"]: r for r in A["res"][repr(mu) if repr(mu) in A["res"] else str(mu)]["rows"]}
        for S in Ss:
            a, ne, gnbar = traj[S]; Jor = R[S]["Jor"]
            Jl = lag_excess(a, NT, NT + ne, mu, s2, w0, L, DELTA)
            e_lag = (Jl - Jor) / Jor; e_gn = mu * gnbar / Jor
            e_st_meas = R[S]["eps_st_traj"]; e3_meas = R[S]["eps3"]
            rho_meas = float(np.mean(R[S]["rho_traj"])) if R[S]["rho_traj"] is not None else None
            pred[(mu, S)] = dict(e_lag=e_lag, e_gn=e_gn, e3_T=e_lag + e_gn, rho_T=e_lag / (plat - e_gn) if plat > e_gn else None,
                                 e3_meas=e3_meas, e_st_meas=e_st_meas, rho_S=e_lag / (plat - e_st_meas) if plat > e_st_meas else None,
                                 rho_meas=rho_meas, lag_meas=e3_meas - e_st_meas)
    # ---- boundary S*_MSE
    lg("S*_MSE (rho_th = 0.5): measured | theory (lag + gradient-noise model) | semi-empirical (lag model + measured static excess)")
    def sstar(vals):
        prev = None
        for S, v in zip(Ss, vals):
            if v is None: return "undef"
            if v >= 0.5: return prev
            prev = S
        return prev
    out_b = {}
    for mu in mus:
        meas = A["res"][repr(mu) if repr(mu) in A["res"] else str(mu)]["mse"]["traj_0.5"][1]
        sT = sstar([pred[(mu, S)]["rho_T"] for S in Ss]); sS = sstar([pred[(mu, S)]["rho_S"] for S in Ss])
        out_b[mu] = (meas, sT, sS)
        lg(f"  mu=2^{np.log2(mu):6.2f}: {str(meas):>5s} | {str(sT):>5s} | {str(sS):>5s}     S*.mu (measured) = {meas * mu if isinstance(meas, (int, float)) else float('nan'):.3f}")
    # ---- lag model check against measurement: measured lag = eps3 - static
    rr = np.array([[p["lag_meas"], p["e_lag"]] for p in pred.values() if p["lag_meas"] > 0.05])
    ratio = rr[:, 1] / rr[:, 0]
    lg(f"lag part, predicted / measured (points with measured lag > 0.05, n = {len(rr)}): median {np.median(ratio):.3f}, 10-90 % {np.percentile(ratio,10):.3f}-{np.percentile(ratio,90):.3f}")
    gg = np.array([[pred[(mu, Ss[0])]["e_gn"], pred[(mu, Ss[0])]["e_st_meas"]] for mu in mus])
    lg("gradient-noise part at the slowest S, theory / measured static excess, per mu: " + " ".join(f"{x/y:.2f}" for x, y in gg))
    json.dump({f"{mu}|{S}": v for (mu, S), v in pred.items()} | {"boundary": {str(k): v for k, v in out_b.items()}, "Ss": Ss, "mus": mus},
              open(f"{OUT}/{tag}.json", "w"), default=float)
    return A, pred, Ss, mus, traj, gn1, w0, s2, plat


def mu_opt_curve(tag, A, traj, s2, w0, Ss, lo, plat, use_measured_static, mus_meas, pred):
    """dense-mu optimum of the model eps3 = eps_lag + eps_gn (theory) or + measured static (interpolated in log mu)."""
    dense = 2.0 ** np.arange(-4.5, -13.01, -0.125)
    res = []
    for S in Ss:
        a, ne, gnbar = traj[S]; Jor = A["res"][list(A["res"])[0]]["rows"][Ss.index(S)]["Jor"]
        lagv = np.array([(lag_excess(a, NT, NT + ne, m, s2, w0, L, DELTA) - Jor) / Jor for m in dense])
        if use_measured_static:
            st = np.array([pred[(m, S)]["e_st_meas"] for m in mus_meas])
            gnv = np.exp(np.interp(np.log(dense), np.log(mus_meas[::-1]) if mus_meas[0] > mus_meas[-1] else np.log(mus_meas), np.log(st[::-1]) if mus_meas[0] > mus_meas[-1] else np.log(st)))
        else:
            gnv = dense * gnbar / Jor
        tot = lagv + gnv; k = int(np.argmin(tot))
        br = 0 < k < len(dense) - 1
        if br:
            x = np.log2(dense[k - 1:k + 2]); y = tot[k - 1:k + 2]; cA, cB, cC = np.polyfit(x, y, 2); lm = -cB / (2 * cA)
        else:
            lm = np.log2(dense[k])
        # local slope of the lag part at the optimum: q = - d log eps_lag / d log mu
        kk = min(max(k, 1), len(dense) - 2)
        q = -(np.log(lagv[kk + 1]) - np.log(lagv[kk - 1])) / (np.log(dense[kk + 1]) - np.log(dense[kk - 1]))
        res.append(dict(S=S, log2mu=float(lm), bracketed=bool(br), q=float(q), lag_at_opt=float(lagv[k]), gn_at_opt=float(gnv[k])))
    return res


if __name__ == "__main__":
    summary = {}
    for tag in ("primary_16", "primary_14", "control_16", "control_14"):
        A, pred, Ss, mus, traj, gn1, w0, s2, plat = analyse(tag)
        lo = 40 if tag.startswith("primary") else 26
        meas = {m["S"]: m for m in A["mu_opt"]}
        used = [S for S in Ss if meas[S]["bracketed"] and meas[S]["rho_at_opt"] <= 0.75]
        log = open(f"{OUT}/{tag}_log.txt", "a")
        for variant, ums in (("theory", False), ("semi-empirical", True)):
            mo = mu_opt_curve(tag, A, traj, s2, w0, Ss, lo, plat, ums, np.array(mus), pred)
            sel = [m for m in mo if m["S"] in used and m["bracketed"]]
            ex = np.polyfit(np.log2([1.0 / m["S"] for m in sel]), [m["log2mu"] for m in sel], 1)[0] if len(sel) >= 4 else float('nan')
            exm = np.polyfit(np.log2([1.0 / S for S in used]), [meas[S]["log2mu_refined"] for S in used], 1)[0]
            line = f"mu_opt exponent over the measured fit range ({len(used)} S values): measured {exm:.3f} | model ({variant}) {ex:.3f}"
            print(line); log.write(line + "\n")
            for m in mo:
                if m["S"] in used:
                    l2 = f"   S={m['S']:5d}: log2 mu_opt measured {meas[m['S']]['log2mu_refined']:6.2f}  model {m['log2mu']:6.2f}  local lag slope q = {m['q']:.2f} -> q/(q+1) = {m['q']/(m['q']+1):.2f}"
                    print(l2); log.write(l2 + "\n")
            summary[f"{tag}|{variant}"] = dict(exp_meas=float(exm), exp_model=float(ex), points=mo, used=used)
        log.close()
    json.dump(summary, open(f"{OUT}/mu_opt_summary.json", "w"), default=float)
