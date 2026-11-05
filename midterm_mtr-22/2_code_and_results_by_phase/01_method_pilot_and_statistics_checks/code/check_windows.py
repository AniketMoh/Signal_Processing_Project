"""FREEZE-1 check 3: exact window lengths, channel-state weighting, seed uncertainty, run-time budget (L1 pilot data used only for uncertainty)."""
import json, numpy as np, re
from sweep import n_eval_for
from lms_lib import triangle_counter
from freeze_grids import S_LIST
from sweep_analyse import *
lo, hi = 40, 116; per1 = 2 * (hi - lo)
print(f"{'S':>5s} {'period':>8s} {'P':>3s} {'N_eval':>8s} {'dev from 152000':>16s}  max |weight - ideal| (11 c-values vs 1/76 interior, 1/152 ends)   N_bits(100 seeds)")
rows = []
for S in S_LIST:
    ne = n_eval_for(S, lo, hi); c = triangle_counter(30000 + ne, 30000, lo, hi, S)[30000:]
    occ = np.bincount(c - lo, minlength=hi - lo + 1) / ne
    ideal = np.ones(hi - lo + 1) / (hi - lo); ideal[0] = ideal[-1] = 0.5 / (hi - lo)
    P = ne // (per1 * S)
    print(f"{S:5d} {per1*S:8d} {P:3d} {ne:8d} {100*(ne-152000)/152000:15.1f}%  {np.abs(occ-ideal).max():.2e}   {100*ne:.2e}")
    rows.append((S, ne))
print("\nweights: interior c-values occupy 2S symbols per period, end values S, i.e. identical to the quasi-static weights used for eps_plateau and the oracle average (max deviation above = 0 up to the final partial step).")
# run-time budget from the pilot log timings (20 seeds): time per S, split into fixed and per-seed parts is unknown, so scale conservatively linearly
t = {}
prev = 0
for ln in open("results/grid_pilot_run_log_16.txt"):
    m = re.match(r"\s+16\|(\S+)\s+N_eval\s+(\d+).*\[(\d+)s\]", ln)
    if m: t[m.group(1)] = (int(m.group(2)), int(m.group(3)) - prev); prev = int(m.group(3))
print("\nBudget (pilot per-S time at 20 seeds, linear scaling to 100 seeds; one SNR; 2 SNRs run in parallel on the 2 cores):")
tot = 0
for S, ne in rows:
    ne0, sec = t[str(S)]; est = sec * 5 * (30000 + ne) / (30000 + ne0); tot += est
    print(f"  S={S:5d}  pilot {sec:3d}s  ->  100 seeds ~ {est/60:5.1f} min")
print(f"  static S=inf ~ {t['None'][1]*5/60:.1f} min; static baselines (11 c) ~ {20*5/60:.1f} min;  total ~ {(tot+t['None'][1]*5+100)/3600:.2f} h per SNR")
# seed uncertainty from the 20-seed pilot at 16 dB: bootstrap half-width of mean rho (traj) near the boundary, scaled by sqrt(20/100) for 100 seeds
D = json.load(open("results/grid_pilot_analysis_16.json"))
print("\nSeed uncertainty (pilot, 20 seeds; 100-seed value ~ x sqrt(0.2) = x0.45): 95% half-width of mean rho at the grid point nearest rho = 0.5, and at S=5000 / S=1000")
for mu in ("0.03125", "0.0078125", "0.001953125", "0.00048828125", "0.000345267"):
    pass
for m, v in D["res"].items():
    mu = float(m); rows_ = v["rows"]
    k = int(np.argmin([abs(r["rho_traj"][0] - 0.5) for r in rows_])); r = rows_[k]
    hw = lambda r: (r["rho_traj"][2] - r["rho_traj"][1]) / 2
    r5 = rows_[0]
    print(f"  mu=2^{np.log2(mu):6.1f}  near boundary S={r['S']:4d} rho {r['rho_traj'][0]:.3f} +/- {hw(r):.4f} (100 seeds ~ {hw(r)*0.45:.4f});   S=5000: rho {r5['rho_traj'][0]:.4f} +/- {hw(r5):.4f}")
