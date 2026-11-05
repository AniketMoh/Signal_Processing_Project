"""Markdown tables of the final L1 results, generated from results/final/analysis_*.json (no hand transcription)."""
import json, numpy as np
from freeze_grids import MU_FLOAT
J = {t: json.load(open(f"results/final/analysis_{t}.json")) for t in ("primary_16", "primary_14", "control_16", "control_14", "primary_12", "primary_14_ber14")}
lab = lambda m: f"2^{np.log2(m):g}"
out = []
out.append("### Table 1 — S*_MSE (ρ_th = 0.5; bands ρ_th 0.25 / 0.75; literal-baseline sensitivity)\n")
out.append("| μ | primary 16 dB | primary 14 dB | primary 12 dB | control 16 dB | control 14 dB |")
out.append("|---|---|---|---|---|---|")
for m in MU_FLOAT:
    cells = []
    for t in ("primary_16", "primary_14", "primary_12", "control_16", "control_14"):
        v = J[t]["res"][str(m)]["mse"]
        a = v["traj_0.5"]
        if a[0].startswith("x"): cells.append("ρ undefined*"); continue
        cells.append(f"**{a[1]}** ({v['traj_0.25'][1]}/{v['traj_0.75'][1]}; lit {v['lit_0.5'][1]})" if a[1] else f"none ({a[3]})")
    out.append(f"| {lab(m)} | " + " | ".join(cells) + " |")
out.append("\n*ρ undefined: the static LMS excess already exceeds the plateau (ε_static ≥ ε_plateau), so the tracking-loss scale has no room.\n")
out.append("### Table 2 — S*_BER (f = 2; primary method = paired seed bootstrap; R = resolved, C = conditional; [a, b] = transition bracket when the boundary point itself is inconclusive, S*_BER not demonstrated under the strict rule)\n")
out.append("| μ | 12 dB (100 seeds) | 14 dB (100 seeds, or 1500 seeds for μ ≤ 2^-7) | 16 dB (100 seeds) | f = 1.5 / 5 at 12 dB |")
out.append("|---|---|---|---|---|")
def cell(b):
    if b["S_star"]: return f"**{b['S_star']}** ({'R' if b['S_star_kind']=='resolved' else 'C'})"
    if b.get("transition_bracket"): return f"n.d. [{b['transition_bracket'][0]}, {b['transition_bracket'][1]}]" + ("" if b["primary"][0] == "P" else " (C)")
    return "n.d. (" + ("reference-limited" if b["primary"][0] in "p" else "non-monotonic") + ")"
for m in MU_FLOAT:
    b12 = J["primary_12"]["res"][str(m)]["ber"]["2.0"]; t14 = "primary_14_ber14" if m <= 2 ** -7 + 1e-15 else "primary_14"
    b14 = J[t14]["res"][str(m)]["ber"]["2.0"]; b16 = J["primary_16"]["res"][str(m)]["ber"]["2.0"]
    r12 = J["primary_12"]["res"][str(m)]["ber"]
    out.append(f"| {lab(m)} | {cell(b12)} | {cell(b14)} | {cell(b16)} | {r12['1.5']['S_star']} / {r12['5.0']['S_star']} |")
out.append("\n### Table 3 — BER status strings (S from 5000 on the left to 1 on the right; P/F/? = resolved pass/fail/inconclusive, p = conditional pass)\n")
out.append("| μ | 12 dB | 14 dB | 16 dB | control 14 dB |")
out.append("|---|---|---|---|---|")
for m in MU_FLOAT:
    t14 = "primary_14_ber14" if m <= 2 ** -7 + 1e-15 else "primary_14"
    out.append(f"| {lab(m)} | `{J['primary_12']['res'][str(m)]['ber']['2.0']['primary']}` | `{J[t14]['res'][str(m)]['ber']['2.0']['primary']}` | `{J['primary_16']['res'][str(m)]['ber']['2.0']['primary']}` | `{J['control_14']['res'][str(m)]['ber']['2.0']['primary']}` |")
out.append("\n### Table 4 — S_cross (paired bootstrap of BER_R3 − min(BER_R1, BER_R2) per S; A = R3 advantage demonstrated, L = loss of advantage confirmed, ? = inconclusive: advantage not demonstrated and no loss confirmed)\n")
out.append("Three different statements must not be confused: (i) **'A at every S'** = R3 advantage demonstrated at every grid point; (ii) **'no crossover confirmed'** = no point is L, but some points may be '?' (advantage not demonstrated there); (iii) **'crossover (L) confirmed'**.\n")
out.append("| run | μ in the run (count; seeds) | μ with A at every S | μ with a confirmed loss (L) | μ with only '?' (no L) | detail for μ without A at every S |")
out.append("|---|---|---|---|---|---|")
for t in ("primary_16", "primary_14", "primary_12", "primary_14_ber14", "control_16", "control_14"):
    mus_ = sorted(J[t]["res"], key=float, reverse=True); nseeds = len(json.load(open(f"results/final_{t}_config.json"))["seeds"])
    allA = [m for m in mus_ if set(J[t]["res"][m]["cross"]["status"]) == {"A"}]
    withL = [m for m in mus_ if "L" in J[t]["res"][m]["cross"]["status"]]
    onlyq = [m for m in mus_ if m not in allA and m not in withL]
    det = "; ".join(f"{lab(float(m))}: status string (S = 5000 … 1) `{J[t]['res'][m]['cross']['status']}`" for m in withL + onlyq[:3]) + (f"; … ({len(onlyq)} μ with only '?')" if len(onlyq) > 3 else "")
    rng = f"{lab(float(mus_[0]))} … {lab(float(mus_[-1]))} ({len(mus_)}; {nseeds} seeds)"
    out.append(f"| {t} | {rng} | {len(allA)} of {len(mus_)} | {len(withL)} | {len(onlyq)} | {det or '—'} |")
out.append("\n### Table 5 — optimum step size exponent d log2 μ_opt / d log2(1/S)\n")
out.append("| run | baseline fit | systematic band (7 variants) | statistical 95 % (seed bootstrap) | points |")
out.append("|---|---|---|---|---|")
for t in ("primary_16", "primary_14", "primary_12", "control_16", "control_14"):
    e = J[t]["exponent"]; v0 = e["variants"]["V0 baseline (3-pt parabola, bracketed, rho<=0.75)"]
    out.append(f"| {t} | {v0[0]:.3f} | {e['variants']['spread'][0]:.3f} – {e['variants']['spread'][1]:.3f} | {e['stat_ci'][0]:.4f} – {e['stat_ci'][1]:.4f} | {v0[1]} |")
open("results/final/tables.md", "w").write("\n".join(out)); print("\n".join(out))
