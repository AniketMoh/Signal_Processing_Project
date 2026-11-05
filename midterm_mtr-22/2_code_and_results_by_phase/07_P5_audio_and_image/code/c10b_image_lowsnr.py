# c10b_image_lowsnr.py -- image payload at LOWER SNR, so that the frozen receiver's progressive degradation and the adaptive receiver's
# failure become visible (owner request 25 Oct).  Level L1, supervised LMS evaluation, primary channel 40-116, Delta = 2, N_T = 30000.
# Same image and bit mapping as c10_image.py.  5 seeds (700001-700005) for the numbers; seed 700001 for the pictures.
# "R3 fails" is used in the two senses defined in the project: (a) BER criterion of PPR-22 Sec. 5.7: R3's BER rises well above its own
# static-channel value (S faster than S*_BER), and (b) S_cross: R3 is no longer better than the controls (only seen for mu = 2^-5, S <= 2).
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from skimage import data, color, transform
from config import CFG, sigma_from_ebn0
from lms_lib import triangle_counter, taps_from_counter, bpsk, apply_channel, make_noise, delayed_symbols, lms_receivers
from exp_lib import prbs
L = CFG["L"]; NT = 30000; OUT = "results/commit"; D = 2
log = open(f"{OUT}/c10b_log.txt", "w")
def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()
img = color.rgb2gray(data.astronaut()); h0 = int(512 * 9 / 16); top = (512 - h0) // 2
img = transform.resize(img[top:top + h0, :], (72, 128), anti_aliasing=True)
pix = np.clip(np.round(img * 255), 0, 255).astype(np.uint8)
bits_img = np.unpackbits(pix.reshape(-1, 1), axis=1).reshape(-1).astype(np.int64); NB = len(bits_img)

def run(S, snr, mu, seed):
    rng = np.random.default_rng(seed)
    bits = np.concatenate([prbs(NT), bits_img, rng.integers(0, 2, D)]).astype(np.int64)
    n_tot = len(bits); x = bpsk(bits)
    c = np.full(n_tot, 40) if S is None else triangle_counter(n_tot, NT, 40, 116, S)
    r = apply_channel(x, taps_from_counter(c, CFG["h2"])) + make_noise(n_tot, sigma_from_ebn0(snr), seed + 500000)
    yA, yF, eA, eF, _ = lms_receivers(r, delayed_symbols(x, D), L, mu, NT, 0, 10 ** 9)
    out = {}
    for nm, y, dl in (("R1", r, 0), ("R2", yF, D), ("R3", yA, D)):
        b = (y[NT + dl: NT + dl + NB] >= 0).astype(np.uint8)
        p = np.packbits(b.reshape(-1, 8), axis=1).reshape(72, 128)
        err = (b != bits_img)
        band = err.reshape(9, -1).mean(axis=1)                  # 9 horizontal bands of 8 rows = 9 consecutive time slices
        out[nm] = dict(img=p, ber=float(err.mean()), nerr=int(err.sum()), bad_pix=int(np.sum(p != pix)),
                       mae=float(np.mean(np.abs(p.astype(int) - pix.astype(int)))), planes=err.reshape(-1, 8).sum(0).tolist(), band=band.tolist())
    return out

SEEDS = range(700001, 700006)
scen = [("static", None, 2.0 ** -8), ("S=1000 (one ramp over the image)", 1000, 2.0 ** -8), ("S=112", 112, 2.0 ** -8),
        ("S=28 (S*_MSE)", 28, 2.0 ** -8), ("S=5", 5, 2.0 ** -8), ("S=1", 1, 2.0 ** -8), ("S=1, mu=2^-5", 1, 2.0 ** -5), ("static, mu=2^-5", None, 2.0 ** -5)]
res = {}
for snr in (12.0, 10.0, 8.0):
    lg(f"=== {snr:.0f} dB (mean over 5 seeds) ===")
    for name, S, mu in scen:
        outs = [run(S, snr, mu, sd) for sd in SEEDS]
        agg = {k: dict(ber=float(np.mean([o[k]["ber"] for o in outs])), bad_pix=float(np.mean([o[k]["bad_pix"] for o in outs])),
                       mae=float(np.mean([o[k]["mae"] for o in outs])), band=np.mean([o[k]["band"] for o in outs], 0).tolist(),
                       planes=np.sum([o[k]["planes"] for o in outs], 0).tolist()) for k in ("R1", "R2", "R3")}
        res[f"{snr}|{name}"] = agg
        lg(f"  {name:34s} BER R1 {agg['R1']['ber']:.2e}  R2 {agg['R2']['ber']:.2e}  R3 {agg['R3']['ber']:.2e} | wrong pixels R1/R2/R3 {agg['R1']['bad_pix']:.0f}/{agg['R2']['bad_pix']:.0f}/{agg['R3']['bad_pix']:.0f} | MAE {agg['R1']['mae']:.2f}/{agg['R2']['mae']:.2f}/{agg['R3']['mae']:.2f}")
        if S == 1000:
            lg("      BER per band of 8 rows (top -> bottom = early -> late):")
            for k in ("R1", "R2", "R3"):
                lg(f"        {k}: " + " ".join(f"{v:.1e}" for v in agg[k]["band"]))
json.dump(res, open(f"{OUT}/c10b.json", "w"))

# pictures at 10 dB, seed 700001
snr = 10.0
fig, axs = plt.subplots(len(scen), 4, figsize=(11, 2.0 * len(scen)))
for i, (name, S, mu) in enumerate(scen):
    o = run(S, snr, mu, 700001)
    axs[i, 0].imshow(pix, cmap='gray', vmin=0, vmax=255); axs[i, 0].set_ylabel(name, fontsize=7)
    for j, k in enumerate(("R1", "R2", "R3")):
        axs[i, j + 1].imshow(o[k]["img"], cmap='gray', vmin=0, vmax=255)
        axs[i, j + 1].set_title(f"{k}: BER {o[k]['ber']:.1e}, {o[k]['bad_pix']} wrong px", fontsize=7)
    for a in axs[i]: a.set_xticks([]); a.set_yticks([])
axs[0, 0].set_title("original", fontsize=7)
fig.suptitle(f"Image payload at {snr:.0f} dB, primary channel, supervised LMS (L1), seed 700001; mu = 2^-8 unless stated", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_C10b_image_{int(snr)}dB.png", dpi=150); plt.close(fig)
# band profile figure for S = 1000
fig, ax = plt.subplots(figsize=(6, 3.6))
for snr_, st in ((12.0, ':'), (10.0, '-'), (8.0, '--')):
    for k, col in (("R1", 'tab:gray'), ("R2", 'tab:red'), ("R3", 'tab:blue')):
        b = res[f"{snr_}|S=1000 (one ramp over the image)"][k]["band"]
        ax.semilogy(np.arange(1, 10), np.maximum(b, 1e-6), st, color=col, label=f"{k} {snr_:.0f} dB")
ax.set_xlabel('band of 8 image rows (1 = top = earliest)'); ax.set_ylabel('BER in the band'); ax.legend(fontsize=6, ncol=3); ax.grid(alpha=.3)
ax.set_title('S = 1000: channel ramps from a = 0.31 to about 0.89 over the image (5 seeds)', fontsize=8)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_C10b_bands.png", dpi=150); plt.close(fig)
