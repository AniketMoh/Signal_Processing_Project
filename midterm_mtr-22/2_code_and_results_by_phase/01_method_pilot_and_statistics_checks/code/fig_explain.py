import json, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from exp_lib import *; from misadj_lib import wiener
from lms_lib import triangle_counter
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
# panel 1: how the channel moves for three S
n = np.arange(0, 60000)
for S, col in ((1000, "tab:blue"), (100, "tab:orange"), (10, "tab:red")):
    c = triangle_counter(60000 + 30000, 30000, 40, 116, S)[30000:]
    ax[0].plot(n, c * 2.0 ** -7, color=col, label=f"S = {S}  (a changes by 2$^{{-7}}$ every {S} symbols)")
ax[0].set_xlabel("symbols after training"); ax[0].set_ylabel("channel coefficient a(n)"); ax[0].legend(fontsize=7, loc="lower right")
ax[0].set_title("1. Smaller S = the same staircase is climbed faster", fontsize=9)
# panel 2: ideal vs LMS weight for small and big mu at S=100
S = 100; N_T = 30000; c = triangle_counter(N_T + 40000, N_T, 40, 116, S)
exp = make_exp_from_counter(c, N_T, 16.0, 1000); s2 = exp["sigma"] ** 2
stride = 50
cols = {2.0 ** -6: "tab:red", 2.0 ** -10: "tab:green"}
idx = None
for mu, col in cols.items():
    out = run_lms(exp, mu, stride); wH = out[4]
    if idx is None:
        wo = np.array([wiener(exp["taps"][k], DELTA, s2)[0] for k in range(0, exp["n_total"], stride)[:wH.shape[0]]])
        k = int(np.argmax(np.abs(wo[-1]))); t = np.arange(wH.shape[0]) * stride
        sl = slice(N_T // stride, (N_T + 20000) // stride)
        ax[1].plot(t[sl] - N_T, wo[sl, k], "k", lw=2, label="ideal (Wiener) weight for the channel right now"); idx = k
    ax[1].plot(t[sl] - N_T, wH[sl, idx], color=col, lw=0.8, label=f"LMS, mu = 2$^{{{int(np.log2(mu))}}}$")
ax[1].set_xlabel("symbols after training"); ax[1].set_ylabel(f"filter weight no. {idx}"); ax[1].legend(fontsize=7)
ax[1].set_title("2. S = 100: big mu follows closely but jitters; small mu is smooth but lags", fontsize=9)
# panel 3: eps vs mu for several S (16 dB pilot)
D = json.load(open("results/grid_pilot_analysis_16.json")); mus = sorted(float(m) for m in D["res"])
for S, col in ((1000, "tab:blue"), (200 if False else 224, "tab:green"), (80, "tab:orange"), (20, "tab:red")):
    y = [100 * next(r["eps3"] for r in D["res"][str(m)]["rows"] if r["S"] == S) for m in mus]
    ax[2].plot(mus, y, "o-", color=col, ms=3, label=f"S = {S}")
ax[2].set_xscale("log", base=2); ax[2].set_yscale("log"); ax[2].set_xlabel("step size mu"); ax[2].set_ylabel("excess MSE over oracle (%)")
ax[2].legend(fontsize=7); ax[2].set_title("3. Each S has a best mu; faster channel -> larger best mu (L1 pilot, 16 dB)", fontsize=9)
plt.tight_layout(); plt.savefig("results/fig_explain_S_and_mu.png", dpi=130)
