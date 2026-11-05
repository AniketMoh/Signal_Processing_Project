"""P6a EXTENSION (G-3, owner decision 20 Oct 23:40): where does finite precision start to limit LMS accuracy and tracking?  Level L2 (bit-true fixed point,
fxp_lib.py; LMS equations unchanged).  Narrow accumulators B_acc in {10, 12, 14} and truncation, at mu in {2^-8, 2^-10}; references B_acc = 16, 26.
Multiplier word: B_mul = min(12, B_acc)  (B_acc = 10 -> B_mul = 10: the multiplier coefficient is the whole accumulator; B_acc >= 12 -> B_mul = 12).
usage: python3 p6b_tests.py T8a | T8b <p>     (p = 8 or 10).  Outputs: results/p6a/T8a.json, T8b_<p>.json + logs.  Data/seeds as T2 (static) and T4 (tracking)."""
import sys, json, time, numpy as np
from exp_lib import *
from lms_lib import triangle_counter
from p6a_tests import build, run_fx, NT
from sweep import n_eval_for
OUT = "results/p6a"
CONFIGS = [(ba, rnd) for rnd in (1, 0) for ba in (10, 12, 14, 16, 26)]          # (B_acc, rounding: 1 nearest, 0 truncation)
bm_of = lambda ba: min(12, ba)
def lg(s, f): print(s, flush=True); f.write(s + "\n"); f.flush()


def T8a():
    f = open(f"{OUT}/T8a_log.txt", "w"); res = {}
    lg("T8a static accuracy and stalls (14 dB, 6 seeds 5610-5615, 100000 evaluation symbols). entries: MSE of L2 relative to L1 in %, and fraction of updates stalled (nonzero exact update rounded to 0).", f)
    for c0 in (40, 116):
        c = np.full(NT + 100000, c0); data = [build(c, 14.0, sd) for sd in range(5610, 5616)]
        for p in (8, 10):
            l1 = np.mean([np.mean(run_lms(ex, 2.0 ** -p, 10 ** 9)[2][NT:] ** 2) for ex, _, _ in data]); Jmin = Rp_const(c0, sigma_from_ebn0(14.0) ** 2)[1]
            lg(f"  c={c0} mu=2^-{p}: L1 MSE {l1:.5f} (excess over J_min {100*(l1/Jmin-1):.1f} %)", f)
            for ba, rnd in CONFIGS:
                J = []; st = up = 0
                for ex, rq, dq in data:
                    yA, yF, eA, eF, wH, s_, u_ = run_fx(ex, rq, dq, p, bm_of(ba), ba, rnd); J.append(np.mean(eA[NT:] ** 2)); st += s_; up += u_
                d = 100 * (np.mean(J) / l1 - 1); res[f"{c0}|{p}|{ba}|{rnd}"] = dict(dJ=d, stall=st / up, J=float(np.mean(J)), J1=float(l1))
                lg(f"     B_acc={ba:2d} B_mul={bm_of(ba):2d} {'nearest ' if rnd else 'truncate'}: MSE vs L1 {d:+8.2f} %   stalled updates {st/up:6.3f}", f)
    json.dump(res, open(f"{OUT}/T8a.json", "w"))


def T8b(p):
    from freeze_grids import STATIC_C
    from sweep_analyse import s_star, interp_matrix
    f = open(f"{OUT}/T8b_{p}_log.txt", "w")
    S_SUB = [5000, 1000, 320, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5]; seeds = list(range(2000, 2020)); snr = 16.0; s2 = sigma_from_ebn0(snr) ** 2; mu = 2.0 ** -p
    plat = plateau_stats(40, 116, s2)["eps_plateau"]; cg = np.array(STATIC_C); A = interp_matrix(cg, np.arange(40, 117))
    Jmin_cg = np.array([Rp_const(c, s2)[1] for c in cg]); rng = np.random.default_rng(5); BI = rng.integers(0, 20, (1000, 20)); res = {}
    lg(f"T8b tracking, 16 dB, mu = 2^-{p}, seeds 2000-2019 (paired with the final L1 data and with T4), rho_th = 0.5, eps_plateau {plat:.3f}.  rho 'undef' = static excess >= plateau", f)
    for ba, rnd in CONFIGS:
        bm = bm_of(ba); t0 = time.time()
        Jst = np.array([np.mean([np.mean(run_fx(*build(np.full(NT + 152000, cc), snr, sd), p, bm, ba, rnd)[2][NT:] ** 2) for sd in seeds]) for cc in cg])
        rows = []
        for S in S_SUB:
            ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
            Jor = float(np.mean(oracle_J_series(taps_from_counter(c, H2), NT, NT + ne, s2)))
            w = np.bincount(c[NT:] - 40, minlength=77) / ne; eps_st = float(w @ (A @ (Jst - Jmin_cg)) / Jor)
            J3 = np.array([np.mean(run_fx(*build(c, snr, sd), p, bm, ba, rnd)[2][NT:] ** 2) for sd in seeds])
            eps = (J3 - Jor) / Jor
            if eps_st >= plat: rows.append(dict(S=S, rho=None, lo=None, hi=None, eps=float(eps.mean()), eps_static=eps_st)); continue
            rho = (eps - eps_st) / (plat - eps_st); m = rho[BI].mean(axis=1)
            rows.append(dict(S=S, rho=float(rho.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), eps=float(eps.mean()), eps_static=eps_st))
        sts = ["u" if r["rho"] is None else ("P" if r["hi"] < 0.5 else ("F" if r["lo"] > 0.5 else "?")) for r in rows]
        Sst = s_star([x if x != "u" else "?" for x in sts], S_SUB, strict=False) if "u" not in sts else (None, False)
        res[f"{ba}|{rnd}"] = dict(rows=rows, status="".join(sts), S_star=Sst[0], B_mul=bm, eps_static_node=list(map(float, (Jst - Jmin_cg) / Jmin_cg)))
        lg(f"  B_acc={ba:2d} B_mul={bm:2d} {'nearest ' if rnd else 'truncate'}: static excess c=40/116 {100*res[f'{ba}|{rnd}']['eps_static_node'][0]:6.1f}/{100*res[f'{ba}|{rnd}']['eps_static_node'][-1]:6.1f} %  eps(%) S=5000: {100*rows[0]['eps']:6.1f}  rho " + " ".join("  undef" if r["rho"] is None else f"{r['rho']:6.2f}" for r in rows) + f"  status {''.join(sts)}  S*_MSE {Sst[0]}   [{time.time()-t0:.0f} s]", f)
    lg("  S grid: " + " ".join(map(str, S_SUB)), f)
    json.dump(res, open(f"{OUT}/T8b_{p}.json", "w"), default=float)


if __name__ == "__main__":
    t0 = time.time(); name = sys.argv[1]
    T8a() if name == "T8a" else T8b(int(sys.argv[2])); print(f"done in {time.time()-t0:.0f} s")
