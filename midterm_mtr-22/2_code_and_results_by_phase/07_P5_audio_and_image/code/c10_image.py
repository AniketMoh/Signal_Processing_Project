# c10_image.py -- PPR-22 Sec. 7.3 image payload, software version (level L1, supervised LMS evaluation as in P5).
# 128 x 72 grayscale, 8 bit/pixel = 73,728 payload bits, raster order (row by row), most significant bit first, so position in the image
# corresponds to time.  Primary channel 40-116, 14 dB, mu = 2^-8, Delta = 2, N_T = 30000 PRBS training, one seed (700001).
# Test image: NASA "astronaut" photograph shipped with scikit-image (public domain), converted to gray, centre-cropped to 16:9 and resized.
# Metrics (PPR-22 Sec. 7.3): BER, incorrect pixel count, mean absolute pixel error, errors per bit plane.
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from skimage import data, color, transform
from config import CFG, sigma_from_ebn0
from lms_lib import triangle_counter, taps_from_counter, bpsk, apply_channel, make_noise, delayed_symbols, lms_receivers
from exp_lib import prbs
L = CFG["L"]; NT = 30000; OUT = "results/commit"; D = 2; SEED = 700001; SNR = 14.0; MU = 2.0 ** -8
log = open(f"{OUT}/c10_log.txt", "w")
def lg(s): print(s, flush=True); log.write(s + "\n"); log.flush()

img = color.rgb2gray(data.astronaut())                  # 512 x 512, values 0..1
h0 = int(512 * 9 / 16); top = (512 - h0) // 2
img = transform.resize(img[top:top + h0, :], (72, 128), anti_aliasing=True)
pix = np.clip(np.round(img * 255), 0, 255).astype(np.uint8)
bits_img = np.unpackbits(pix.reshape(-1, 1), axis=1).reshape(-1).astype(np.int64)   # MSB first
NB = len(bits_img); assert NB == 73728

def run(S):
    rng = np.random.default_rng(SEED)
    pad = rng.integers(0, 2, D)                          # D extra symbols so that the last payload bits leave the R2/R3 delay line
    bits = np.concatenate([prbs(NT), bits_img, pad]).astype(np.int64)
    n_tot = len(bits); x = bpsk(bits)
    c = np.full(n_tot, 40) if S is None else triangle_counter(n_tot, NT, 40, 116, S)
    r = apply_channel(x, taps_from_counter(c, CFG["h2"])) + make_noise(n_tot, sigma_from_ebn0(SNR), SEED + 500000)
    yA, yF, eA, eF, _ = lms_receivers(r, delayed_symbols(x, D), L, MU, NT, 0, 10 ** 9)
    out = {}
    for nm, y, dl in (("R1 direct", r, 0), ("R2 frozen", yF, D), ("R3 adaptive", yA, D)):
        b = (y[NT + dl: NT + dl + NB] >= 0).astype(np.uint8)
        p = np.packbits(b.reshape(-1, 8), axis=1).reshape(72, 128)
        err = b != bits_img
        planes = err.reshape(-1, 8).sum(axis=0)          # index 0 = MSB
        out[nm] = dict(img=p, ber=float(err.mean()), nerr=int(err.sum()), bad_pix=int(np.sum(p != pix)),
                       mae=float(np.mean(np.abs(p.astype(int) - pix.astype(int)))), planes=planes.tolist())
    return out, c

scen = [("static (c = 40)", None), ("S = 1000", 1000), ("S = 28 (boundary, mu = 2^-8)", 28), ("S = 5", 5), ("S = 1", 1)]
res = {}
fig, axs = plt.subplots(len(scen), 4, figsize=(11, 2.0 * len(scen)))
for i, (name, S) in enumerate(scen):
    out, c = run(S)
    res[name] = {k: {kk: vv for kk, vv in v.items() if kk != "img"} for k, v in out.items()}
    lg(f"{name}: " + " | ".join(f"{k}: BER {v['ber']:.2e} ({v['nerr']} bit errors), wrong pixels {v['bad_pix']}, MAE {v['mae']:.2f}, errors per bit plane MSB..LSB {v['planes']}" for k, v in out.items()))
    axs[i, 0].imshow(pix, cmap='gray', vmin=0, vmax=255); axs[i, 0].set_ylabel(name, fontsize=8)
    for j, k in enumerate(("R1 direct", "R2 frozen", "R3 adaptive")):
        axs[i, j + 1].imshow(out[k]["img"], cmap='gray', vmin=0, vmax=255)
        axs[i, j + 1].set_title(f"{k}: BER {out[k]['ber']:.1e}", fontsize=7)
    axs[i, 0].set_title("original" if i == 0 else "", fontsize=7)
    for a in axs[i]: a.set_xticks([]); a.set_yticks([])
fig.suptitle(f"Image payload 128x72x8 bit, primary channel, {SNR:.0f} dB, mu = 2^-8, supervised LMS evaluation (L1), one seed", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_C10_image.png", dpi=150); plt.close(fig)
plt.imsave(f"{OUT}/image_original_128x72.png", pix, cmap='gray', vmin=0, vmax=255)
json.dump(res, open(f"{OUT}/c10.json", "w"))
