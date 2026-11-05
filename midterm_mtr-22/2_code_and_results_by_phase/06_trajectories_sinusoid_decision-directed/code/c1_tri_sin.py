# c1_tri_sin.py -- PPR-22 Sec. 4.2: "The floating-point model will confirm that the two [triangular and sinusoidal trajectories]
# give comparable tracking behaviour at matched average rates of change."   Level L1, primary channel a in [40, 116]*2^-7, supervised LMS.
#   triangle : counter steps +-1 every S symbols (average |da/dn| = 2^-7/S), period 152*S
#   sinusoid : a[n] = a_mid - A cos(2 pi (n - N_T)/T), same extremes, same start (minimum) and same period T = 152*S
#              -> same average |da/dn| = 4A/T = 2^-7/S; its peak rate is pi/2 times larger.  Not quantised to the 2^-7 grid.
#   sinusoid (peak-matched): period stretched by pi/2 so that its PEAK rate equals the triangle's rate (sensitivity case)
# Metrics: oracle-normalised excess MSE eps = J/J_oracle - 1 for R3 and R2 at 16 dB; BER of R1/R2/R3 at 14 dB.  20 seeds (2000-2019).
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from config import CFG, DA, sigma_from_ebn0
from lms_lib import triangle_counter, taps_from_counter, bpsk, make_bits, make_noise, apply_channel, delayed_symbols, lms_receivers
from exp_lib import prbs, oracle_J_series
L = CFG["L"]; NT = 30000; OUT = "results/commit"; log = open(f"{OUT}/c1_log.txt", "a" if "plot" in __import__("sys").argv else "w")
def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()
A_LO, A_HI = 40 * DA, 116 * DA; A_MID = (A_LO + A_HI) / 2; AMP = (A_HI - A_LO) / 2

def a_traj(shape, S, n_tot):
    a = np.full(n_tot, A_LO)
    if shape == "triangle":
        return triangle_counter(n_tot, NT, 40, 116, S) * DA
    T = 152 * S * (np.pi / 2 if shape == "sine_peak" else 1.0)
    n = np.arange(NT, n_tot)
    a[NT:] = A_MID - AMP * np.cos(2 * np.pi * (n - NT) / T)
    return a

def n_eval(shape, S):
    T = 152 * S * (np.pi / 2 if shape == "sine_peak" else 1.0)
    k = max(1, round(152000 / T)); return int(round(k * T))

def run(shape, S, mus, snr, seeds):
    ne = n_eval(shape, S); n_tot = NT + ne
    a = a_traj(shape, S, n_tot)
    taps = np.zeros((n_tot, 3)); taps[:, 0] = 1.0; taps[:, 1] = a; taps[:, 2] = CFG["h2"]
    s2 = sigma_from_ebn0(snr) ** 2
    Jor = float(np.mean(oracle_J_series(taps, NT, n_tot, s2)))
    out = {m: dict(J3=[], J2=[], e1=0, e2=0, e3=0, n=0) for m in mus}
    for sd in seeds:
        bits = np.concatenate([prbs(NT), make_bits(ne, sd)]).astype(np.int64); x = bpsk(bits)
        r = apply_channel(x, taps) + make_noise(n_tot, np.sqrt(s2), sd + 500000)
        d = delayed_symbols(x, 2)
        ref = np.zeros(n_tot, np.int64); ref[2:] = bits[:-2]
        e1 = int(np.sum((r[NT:] >= 0).astype(int) != bits[NT:]))
        for m in mus:
            yA, yF, eA, eF, wH = lms_receivers(r, d, L, m, NT, 0, 10 ** 9)
            o = out[m]; o["J3"].append(np.mean(eA[NT:] ** 2)); o["J2"].append(np.mean(eF[NT:] ** 2))
            o["e3"] += int(np.sum((yA[NT:] >= 0).astype(int) != ref[NT:])); o["e2"] += int(np.sum((yF[NT:] >= 0).astype(int) != ref[NT:]))
            o["e1"] += e1; o["n"] += ne
    return Jor, out

import sys
mus = [2.0 ** -6, 2.0 ** -8, 2.0 ** -10]; Sg = [1000, 320, 112, 56, 28, 14, 5]; seeds = list(range(2000, 2020)); res = {}
PLOT_ONLY = len(sys.argv) > 1 and sys.argv[1] == "plot"
if PLOT_ONLY: res = json.load(open(f"{OUT}/c1.json"))
for snr in (() if PLOT_ONLY else (16.0, 14.0)):
    lg(f"=== {snr:.0f} dB ===")
    for S in Sg:
        for shape in ("triangle", "sine", "sine_peak"):
            Jor, out = run(shape, S, mus, snr, seeds)
            for m in mus:
                o = out[m]; key = f"{snr}|{S}|{shape}|{m}"
                J3 = np.array(o["J3"]); eps3 = J3 / Jor - 1; eps2 = np.mean(o["J2"]) / Jor - 1
                res[key] = dict(Jor=Jor, eps3=float(eps3.mean()), eps3_se=float(eps3.std(ddof=1) / np.sqrt(len(eps3))), eps2=float(eps2),
                                ber1=o["e1"] / o["n"], ber2=o["e2"] / o["n"], ber3=o["e3"] / o["n"], e3=o["e3"], n=o["n"])
        for m in mus:
            t = res[f"{snr}|{S}|triangle|{m}"]; s = res[f"{snr}|{S}|sine|{m}"]; q = res[f"{snr}|{S}|sine_peak|{m}"]
            if snr == 16.0:
                lg(f"  S={S:5d} mu=2^{np.log2(m):.0f}: eps_R3 triangle {t['eps3']:.4f}+-{t['eps3_se']:.4f} | sine {s['eps3']:.4f}+-{s['eps3_se']:.4f} (ratio {s['eps3']/t['eps3'] if t['eps3']>0 else float('nan'):.2f}) | sine peak-matched {q['eps3']:.4f} (ratio {q['eps3']/t['eps3'] if t['eps3']>0 else float('nan'):.2f}) | eps_R2 tri/sine {t['eps2']:.3f}/{s['eps2']:.3f}")
            else:
                lg(f"  S={S:5d} mu=2^{np.log2(m):.0f}: BER R3 triangle {t['ber3']:.2e} ({t['e3']} err) | sine {s['ber3']:.2e} ({s['e3']}) | sine peak-matched {q['ber3']:.2e} ({q['e3']}) | R2 tri/sine {t['ber2']:.2e}/{s['ber2']:.2e} | R1 tri/sine {t['ber1']:.2e}/{s['ber1']:.2e}")
if not PLOT_ONLY: json.dump(res, open(f"{OUT}/c1.json", "w"))

# figure: eps_R3 vs S at 16 dB
fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
for ax, m in zip(axs, mus):
    for shape, st in (("triangle", 'o-'), ("sine", 's--'), ("sine_peak", '^:')):
        ax.loglog(Sg, [max(res[f"16.0|{S}|{shape}|{m}"]["eps3"], 1e-4) for S in Sg], st, label={"triangle": "triangle", "sine": "sine, average-rate matched", "sine_peak": "sine, peak-rate matched"}[shape])
    ax.invert_xaxis(); ax.set_xlabel('S (symbols per counter step; faster to the right)'); ax.set_title(f"mu = 2^{np.log2(m):.0f}", fontsize=9); ax.grid(alpha=.3, which='both')
axs[0].set_ylabel('R3 oracle-normalised excess MSE'); axs[0].legend(fontsize=7)
fig.suptitle('Triangle vs sinusoid trajectory, primary channel, 16 dB, 20 seeds (L1)', fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_C1_tri_vs_sin.png", dpi=150); plt.close(fig)
