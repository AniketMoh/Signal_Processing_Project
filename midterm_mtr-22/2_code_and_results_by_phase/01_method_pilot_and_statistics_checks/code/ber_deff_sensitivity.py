"""AUDIT (analysis only, no new simulation): how do the grid-pilot BER statuses and S*_BER change if the Wilson intervals are
widened by the error-burst design effect measured in check_error_independence.py?  Approximation: k -> k/D, N -> N/D (same BER, fewer
independent units). D = 1.9 for mu >= 2^-6 (measured 1.70-1.87 at 2^-5; 2^-5.5 and 2^-6 not measured -> conservative), D = 1.25 for mu <= 2^-6.5
(measured 1.07-1.22).  Reference side treated the same way (resolved rule uses the raw expected count).  Also prints R2 vs R3 at the static
control and S = 5000 (PPR-22 Sec. 5.5: conditions where R2 matches or beats R3).  Run from code/: python3 audit/ber_deff_sensitivity.py"""
import sys, json; sys.path.insert(0, ".")
import numpy as np
from sweep_analyse import wilson, s_star
from freeze_grids import S_LIST, MU_FLOAT
for snr in (16, 14):
    D_ = json.load(open(f"results/grid_pilot_analysis_{snr}.json")); RAW = np.load(f"results/grid_pilot_raw_{snr}.npz")
    print(f"\n===== {snr} dB grid pilot (L1 pilot, 20 seeds), f = 2, trajectory reference (linear interpolation, as in the pilot analysis)")
    changed = 0
    for mu in MU_FLOAT:
        r = D_["res"][str(mu)]; D = 1.9 if mu >= 2 ** -6 else 1.25
        sts = []
        for row in r["rows"]:
            T = 2 * (row["ref_obs"] if row["resolved"] else row["ref_ub"])
            l, u = wilson(row["E3"] / D, row["N_bits"] / D)
            s = "P" if u <= T else ("F" if l > T else "?")
            sts.append(s.lower() if (s == "P" and not row["resolved"]) else s)
        new = "".join(sts); old = r["ber"]["2.0"][0]
        Snew = s_star(sts, S_LIST, strict=True)[0]; Sold = r["ber"]["2.0"][1]
        diff = "".join("^" if a != b else " " for a, b in zip(old, new))
        changed += sum(a != b for a, b in zip(old, new))
        print(f"  mu=2^{np.log2(mu):5.1f} D={D:4.2f}  plain {old}  S*_BER {Sold}\n                       burst {new}  S*_BER {Snew}\n                             {diff}")
    print(f"  total status changes: {changed} of {len(MU_FLOAT)*len(S_LIST)} grid points")
    print("  R2 vs R3 MSE and BER at the static control (S = inf) and at S = 5000 (pooled over 20 seeds):")
    for S in ("None", "5000"):
        for i, mu in enumerate(MU_FLOAT):
            if i % 3: continue
            k = f"{snr}|{S}"; J2 = RAW[k + "|J2"][i].mean(); J3 = RAW[k + "|J3"][i].mean(); E2 = RAW[k + "|E2"][i].sum(); E3 = RAW[k + "|E3"][i].sum()
            print(f"     S={S:>5s} mu=2^{np.log2(mu):5.1f}: MSE R2 {J2:.5f}  R3 {J3:.5f}  ({'R2 better' if J2 < J3 else 'R3 better'});  errors R2 {E2}  R3 {E3}")
