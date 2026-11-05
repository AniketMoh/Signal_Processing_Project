# c10c_image_fig.py -- compact 4-row version of the 10 dB image figure for the report (same run function and seed as c10b_image_lowsnr.py)
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import importlib.util, sys, types
src = open('c10b_image_lowsnr.py').read().split("SEEDS = range")[0]          # definitions only (image, run), not the experiment loop
mod = types.ModuleType("c10b_defs"); exec(compile(src.replace('log = open(f"{OUT}/c10b_log.txt", "w")', 'log = None'), "c10b_defs", "exec"), mod.__dict__)
scen = [("static, mu=2^-8", None, 2.0 ** -8), ("S=1000, mu=2^-8", 1000, 2.0 ** -8), ("S=1, mu=2^-8", 1, 2.0 ** -8), ("S=1, mu=2^-5", 1, 2.0 ** -5)]
fig, axs = plt.subplots(4, 4, figsize=(10, 6.2))
for i, (name, S, mu) in enumerate(scen):
    o = mod.run(S, 10.0, mu, 700001)
    axs[i, 0].imshow(mod.pix, cmap='gray', vmin=0, vmax=255); axs[i, 0].set_ylabel(name, fontsize=8)
    for j, k in enumerate(("R1", "R2", "R3")):
        axs[i, j + 1].imshow(o[k]["img"], cmap='gray', vmin=0, vmax=255)
        axs[i, j + 1].set_title(f"{k}: BER {o[k]['ber']:.1e}, {o[k]['bad_pix']} px", fontsize=8)
    for a in axs[i]: a.set_xticks([]); a.set_yticks([])
axs[0, 0].set_title("original", fontsize=8)
fig.tight_layout(); fig.savefig('results/commit/fig_C10c_image_sel.png', dpi=150)
