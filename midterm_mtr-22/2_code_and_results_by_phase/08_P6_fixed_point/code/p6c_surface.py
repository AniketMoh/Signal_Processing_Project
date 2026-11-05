"""P6 completion (owner instruction 24 Oct 2026: finish the PPR-22 commitments).  Level L2 (bit-true fixed point, fxp_lib.py; LMS equations unchanged).
PPR-22 Sec. 6.4/10.2: S* against coefficient word length.  Same method, data, seeds and S grid as T8b (p6b_tests.py), extended to
  * all seven power-of-two step sizes mu = 2^-5 ... 2^-11 (the FPGA set), and
  * two word-length families:
      family A (accumulator width, multiplier 12 bits):  B_acc in {10, 12, 14, 16, 26}, B_mul = min(12, B_acc), rounding and truncation
      family B (multiplier width, the PPR-22 "8, 12, 16 bits"): B_mul in {8, 12, 16} with a wide accumulator B_acc = 26, rounding and truncation
usage: python3 p6c_surface.py <p> <family A|B>     outputs results/p6c/surface_<family>_<p>.json and _log.txt (never overwrites T8b files)."""
import sys, os, json, time, numpy as np
from exp_lib import *
from lms_lib import triangle_counter
from p6a_tests import build, run_fx, NT
from sweep import n_eval_for
from freeze_grids import STATIC_C
from sweep_analyse import s_star, interp_matrix

OUT = "results/p6c"; os.makedirs(OUT, exist_ok=True)
FAMILY = {"A": [(ba, min(12, ba), rnd) for rnd in (1, 0) for ba in (10, 12, 14, 16, 26)],
          "B": [(26, bm, rnd) for rnd in (1, 0) for bm in (8, 12, 16)]}
def lg(s, f): print(s, flush=True); f.write(s + "\n"); f.flush()


def surface(p, fam):
    f = open(f"{OUT}/surface_{fam}_{p}_log.txt", "w")
    S_SUB = [5000, 1000, 320, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5]; seeds = list(range(2000, 2020)); snr = 16.0; s2 = sigma_from_ebn0(snr) ** 2
    plat = plateau_stats(40, 116, s2)["eps_plateau"]; cg = np.array(STATIC_C); A = interp_matrix(cg, np.arange(40, 117))
    Jmin_cg = np.array([Rp_const(c, s2)[1] for c in cg]); rng = np.random.default_rng(5); BI = rng.integers(0, 20, (1000, 20)); res = {}
    lg(f"P6 surface family {fam}, 16 dB, mu = 2^-{p}, seeds 2000-2019, rho_th = 0.5, eps_plateau {plat:.3f}.  status per S: P pass, F fail, ? inconclusive, u = rho undefined (static excess >= plateau)", f)
    for ba, bm, rnd in FAMILY[fam]:
        t0 = time.time()
        Jst = np.array([np.mean([np.mean(run_fx(*build(np.full(NT + 152000, cc), snr, sd), p, bm, ba, rnd)[2][NT:] ** 2) for sd in seeds]) for cc in cg])
        rows = []
        for S in S_SUB:
            ne = n_eval_for(S, 40, 116); c = triangle_counter(NT + ne, NT, 40, 116, S)
            Jor = float(np.mean(oracle_J_series(taps_from_counter(c, H2), NT, NT + ne, s2)))
            w = np.bincount(c[NT:] - 40, minlength=77) / ne; eps_st = float(w @ (A @ (Jst - Jmin_cg)) / Jor)
            J3 = np.array([np.mean(run_fx(*build(c, snr, sd), p, bm, ba, rnd)[2][NT:] ** 2) for sd in seeds])
            eps = (J3 - Jor) / Jor
            if eps_st >= plat:
                rows.append(dict(S=S, rho=None, lo=None, hi=None, eps=float(eps.mean()), eps_static=eps_st)); continue
            rho = (eps - eps_st) / (plat - eps_st); m = rho[BI].mean(axis=1)
            rows.append(dict(S=S, rho=float(rho.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)), eps=float(eps.mean()), eps_static=eps_st))
        sts = ["u" if r["rho"] is None else ("P" if r["hi"] < 0.5 else ("F" if r["lo"] > 0.5 else "?")) for r in rows]
        Sst = s_star(sts, S_SUB, strict=False) if "u" not in sts else (None, False)
        key = f"{ba}|{bm}|{rnd}"
        res[key] = dict(rows=rows, status="".join(sts), S_star=Sst[0], B_acc=ba, B_mul=bm, rnd=rnd,
                        eps_static_node=list(map(float, (Jst - Jmin_cg) / Jmin_cg)))
        lg(f"  B_acc={ba:2d} B_mul={bm:2d} {'nearest ' if rnd else 'truncate'}: static excess c=40/116 {100*res[key]['eps_static_node'][0]:8.1f}/{100*res[key]['eps_static_node'][-1]:8.1f} %  status {''.join(sts)}  S*_MSE {Sst[0]}   [{time.time()-t0:.0f} s]", f)
    lg("  S grid: " + " ".join(map(str, S_SUB)), f)
    json.dump(res, open(f"{OUT}/surface_{fam}_{p}.json", "w"), default=float)


if __name__ == "__main__":
    surface(int(sys.argv[1]), sys.argv[2])
