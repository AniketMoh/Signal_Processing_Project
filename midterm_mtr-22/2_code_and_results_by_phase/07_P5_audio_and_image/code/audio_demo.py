"""P5 -- recorded-audio demonstration (level L1, SUPERVISED LMS, LMS loop unchanged).
MODE: SUPERVISED LMS.  In this software experiment the adaptive equalizer R3 is given the KNOWN transmitted bits as its desired signal d[n]
(e[n] = d[n] - y[n]) during training AND during the whole payload.  A real receiver does not have these bits during the payload; a
decision-directed (blind) mode is not used here and is not claimed.  R2 is frozen at the end of training.  Level L1: floating point,
ideal Gaussian noise; no hardware or fixed-point result.
The owner's own voice recording is the payload.  Pipeline:
  1. convert the recording (any format ffmpeg reads) to 8 kHz, mono, 8-bit unsigned PCM  -> results/p5/original_8k.wav
  2. bits = 8 bits per sample, most significant bit first
  3. link: 30000-symbol PRBS training, then the audio bits; time-varying ISI channel [1, a[n], 0.1]; Gaussian noise (L1)
  4. R1 (direct), R2 (frozen at N_T), R3 (adaptive LMS) on the SAME received samples
  5. reconstruct the audio from each receiver's decisions -> results/p5/<scenario>_R1.wav, _R2.wav, _R3.wav
Metrics per receiver: BER over the payload, waveform SNR against the converted original, errors per bit plane.
usage:  python3 audio_demo.py <recording> [S_boundary]        (S_boundary = S near the measured boundary for mu = 2^-8, 14 dB)
        python3 audio_demo.py --selftest                        (DEBUG ONLY: temporary test tone, written to the scratch folder,
                                                                  never presented as the P5 result)"""
import sys, os, json, subprocess, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.io import wavfile
from exp_lib import *
from lms_lib import triangle_counter

EB = 14.0; MU = 2.0 ** -8; N_T = 30000; SEED = 700000; C_LO, C_HI = 40, 116; PAD = 16


def convert(path, out_wav):
    """Any input -> 8 kHz mono unsigned 8-bit PCM WAV (ffmpeg)."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "8000", "-acodec", "pcm_u8", out_wav], check=True)
    fs, a = wavfile.read(out_wav)
    assert fs == 8000 and a.dtype == np.uint8 and a.ndim == 1, (fs, a.dtype, a.shape)
    return a


def run_link(payload_bits, S):
    """Training + payload (+ PAD random bits so that the last payload bits leave the equalizer delay line)."""
    pad = make_bits(PAD, SEED + 1)
    bits = np.concatenate([prbs(N_T), payload_bits, pad]).astype(np.int64)
    n_total = len(bits)
    c = triangle_counter(n_total, N_T, C_LO, C_HI, S)
    x = bpsk(bits); taps = taps_from_counter(c, H2); sigma = sigma_from_ebn0(EB)
    r = apply_channel(x, taps) + make_noise(n_total, sigma, SEED + 500000)
    ex = dict(bits=bits, x=x, c=c, taps=taps, r=r, sigma=sigma, N_T=N_T, n_total=n_total)
    yA, yF, eA, eF, _ = run_lms(ex, MU, 10 ** 9)
    nb = len(payload_bits); j = np.arange(nb)
    est = {"R1": (r[N_T + j] >= 0).astype(np.uint8),                       # direct detector: delay 0
           "R2": (yF[N_T + j + DELTA] >= 0).astype(np.uint8),              # equalizers: decision delay Delta = 2
           "R3": (yA[N_T + j + DELTA] >= 0).astype(np.uint8)}
    return est, c[N_T:N_T + nb]


def metrics(orig_u8, bits, est_bits):
    rec = np.packbits(est_bits)[:len(orig_u8)]
    err = est_bits != bits
    planes = err.reshape(-1, 8).sum(axis=0)                                 # index 0 = MSB (bit 7)
    xo = orig_u8.astype(float) - 128; xr = rec.astype(float) - 128
    den = np.sum((xo - xr) ** 2)
    snr = float('inf') if den == 0 else 10 * np.log10(np.sum(xo ** 2) / den)        # inf = reconstruction identical to the original
    return rec, dict(bit_errors=int(err.sum()), bits=int(len(bits)), BER=float(err.mean()), waveform_SNR_dB=float(snr),
                     errors_per_bit_plane_MSB_first=[int(v) for v in planes])


def main(src, S_boundary, outdir, label):
    os.makedirs(outdir, exist_ok=True)
    orig = convert(src, os.path.join(outdir, "original_8k.wav"))
    bits = np.unpackbits(orig)                                              # MSB first
    print(f"{label}: {len(orig)} samples = {len(orig)/8000:.2f} s, {len(bits)} payload bits; Eb/N0 {EB} dB, mu 2^-8, primary channel c {C_LO}-{C_HI}")
    scen = {"static": None, "slow_S1000": 1000, f"boundary_S{S_boundary}": S_boundary, "fast_S1": 1}
    allm = {}; fig, ax = plt.subplots(len(scen) + 1, 1, figsize=(11, 2.0 * (len(scen) + 1)), sharex=True)
    t = np.arange(len(orig)) / 8000
    ax[0].plot(t, orig.astype(int) - 128, lw=0.4, color="0.3"); ax[0].set_ylabel("original\n(8-bit)"); ax[0].set_title(f"P5 {label}  |  L1 simulation, Gaussian noise  |  SUPERVISED LMS (known transmitted bits used as reference)  |  14 dB, mu 2^-8", fontsize=9)
    for si, (nm, S) in enumerate(scen.items()):
        est, cpath = run_link(bits, S); allm[nm] = {}
        for rx in ("R1", "R2", "R3"):
            rec, m = metrics(orig, bits, est[rx]); allm[nm][rx] = m
            wavfile.write(os.path.join(outdir, f"{nm}_{rx}.wav"), 8000, rec)
        a = ax[si + 1]
        for k, (rx, col) in enumerate((("R1", "tab:red"), ("R2", "tab:orange"), ("R3", "tab:green"))):
            errpos = np.flatnonzero(est[rx] != bits) // 8 / 8000
            a.plot(errpos, np.full(len(errpos), k), "|", color=col, ms=6, label=f"{rx}: BER {allm[nm][rx]['BER']:.1e}")
        a2 = a.twinx(); a2.set_ylabel("a[n]", fontsize=8)
        if S is not None and S < 20:                                        # fast channel: draw the channel as a light band (min-max), otherwise it hides the error marks
            blk = 2000 * max(S, 1); nb_ = len(cpath) // blk * blk
            cb = (cpath[:nb_] * DA).reshape(-1, blk); tb = (np.arange(cb.shape[0]) + 0.5) * blk / 64000
            a2.fill_between(tb, cb.min(axis=1), cb.max(axis=1), color="0.8", alpha=0.7, lw=0)
        else:
            a2.plot(np.arange(len(cpath)) / 64000, cpath * DA, color="0.6", lw=0.8)
        a.set_zorder(a2.get_zorder() + 1); a.patch.set_visible(False)       # error marks on top of the channel trace
        a.set_yticks([0, 1, 2]); a.set_yticklabels(["R1", "R2", "R3"]); a.set_ylim(-0.7, 2.7); a.set_ylabel(nm, fontsize=8); a.legend(fontsize=7, loc="lower right", ncol=3, framealpha=0.9)
        print(f"  {nm:16s} " + "  ".join(f"{rx}: BER {allm[nm][rx]['BER']:.2e} SNR {allm[nm][rx]['waveform_SNR_dB']:5.1f} dB" for rx in ("R1", "R2", "R3")))
    ax[-1].set_xlabel("time in the recording (s)   (error marks; grey = channel coefficient a[n])")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "fig_P5_audio.png"), dpi=120)
    open(os.path.join(outdir, "README_P5.txt"), "w").write(
        "P5 recorded-audio demonstration (" + label + ")\nLevel L1 simulation: floating point, ideal Gaussian noise, Eb/N0 14 dB, mu 2^-8, primary channel c 40-116.\n"
        "MODE: SUPERVISED LMS. The adaptive receiver R3 uses the KNOWN transmitted bits as its reference during training and during the payload (software experiment only).\n"
        "R1 = direct detector, R2 = equalizer frozen after training, R3 = adaptive LMS equalizer. All three see the same received samples.\n"
        "Files: original_8k.wav (converted original), <scenario>_R1/R2/R3.wav (reconstructions), p5_metrics.json, fig_P5_audio.png.\n")
    json.dump(dict(note='waveform_SNR_dB = Infinity means the reconstruction is bit-identical to the converted original', mode='SUPERVISED LMS: the known transmitted bits are the desired signal during training and payload (software experiment); R2 frozen at N_T; level L1 (floating point, Gaussian noise); not a hardware or fixed-point result', label=label, EbN0_dB=EB, mu=MU, N_T=N_T, seed=SEED, channel=[C_LO, C_HI], scenarios=scen, metrics=allm),
              open(os.path.join(outdir, "p5_metrics.json"), "w"), indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "--selftest":
        d = "/tmp/claude-0/-home-claude/fcb77b13-4e1c-5380-ba88-caf3ff78d7f3/scratchpad/p5_debug"; os.makedirs(d, exist_ok=True)
        tt = np.arange(0, 2.0, 1 / 16000); tone = 0.4 * np.sin(2 * np.pi * 440 * tt) * np.sin(2 * np.pi * 1.5 * tt)
        wavfile.write(os.path.join(d, "debug_tone.wav"), 16000, (tone * 32767).astype(np.int16))
        main(os.path.join(d, "debug_tone.wav"), 28, d, "DEBUG test tone (not a P5 result)")
    else:
        main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 28, "results/p5", "owner's voice recording")
