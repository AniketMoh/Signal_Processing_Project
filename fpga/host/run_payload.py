# run_payload.py -- audio, image and live-microphone payloads through the Boolean Board (level L5, supervised LMS).
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
#   python run_payload.py audio     the P5 voice recording (8 kHz, 8-bit) for the P5 scenarios; board decisions checked against L2
#   python run_payload.py image     the P5 128x72 8-bit image for the P5 image scenarios; checked against L2
#   python run_payload.py live      the laptop microphone, streamed in real time; the board plays the receiver selected by
#                                   SW[11:10] (0 R3, 1 R2, 2 R1) on its audio jack; optional playback on the PC (--pc-play)
# Options: --port COMx, audio: --file my_clip.mp3 [--max-seconds 20] (your own clip; results in results/payload/custom_<name>/),
#           --no-l2 (skip the bit-true comparison), live: --seconds, --S, --p, --ebn0, --pc-play R1|R2|R3
# The payload goes out MSB first (np.unpackbits order) with one padding byte; the board returns per payload byte one word
# (R1, R2, R3 bytes) with the receiver delays removed, so byte j of each stream is that receiver's copy of payload byte j.
# Live audio is a demonstration (not repeatable), never a measurement for the tracking results.
import argparse, json, os, queue, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
import numpy as np
from scipy.io import wavfile
import protocol as P
from run_board import Board, find_port

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
P5 = os.path.join(REPO, "midterm_mtr-22", "2_code_and_results_by_phase", "07_P5_audio_and_image")
OUT = os.path.join(HERE, "results", "payload")
WINDOW = 3000                     # payload bytes in flight at most (board input buffer: 4096)
N_T = 30000
C_LO, C_HI = 40, 116


def stream(board, frame, data, rate=None, source=None, on_words=None, quiet_end=3.0):
    """Send 'frame' and then the payload (data + one padding byte, or bytes from 'source' for live audio), keep at most WINDOW
    bytes in flight, and collect the decision words and the final report.  rate: bytes/s pacing (None = as fast as the link).
    source: a queue of byte strings (live); a None item ends the stream.  Returns (R1, R2, R3 byte strings, report, seconds)."""
    s = board.s
    s.reset_input_buffer()
    s.write(frame)
    sent, out, t0, last = 0, bytearray(), time.time(), time.time()
    buf = bytearray(data) if source is None else bytearray()
    ended = source is None
    if ended:
        buf += b"\x00"
    while True:
        if not ended:
            try:
                while True:
                    item = source.get_nowait()
                    if item is None:
                        ended = True; buf += b"\x00"; break
                    buf += item
            except queue.Empty:
                pass
        words = len(out) // 3
        allow = words + WINDOW - sent
        if rate:
            allow = min(allow, int((time.time() - t0) * rate) + 64 - sent)
        k = min(allow, len(buf) - sent, 256)          # small writes: never block long while data is coming back
        if k > 0:
            s.write(bytes(buf[sent:sent + k])); sent += k
        chunk = s.read(max(1, s.in_waiting))
        if chunk:
            prev = len(out) // 3
            out += chunk; last = time.time()
            if on_words and len(out) // 3 > prev:
                on_words(out, prev, len(out) // 3)
        n_data = sent - 1 if ended and sent == len(buf) else None
        if n_data is not None and len(out) >= 3 * n_data + P.REPORT_LEN:
            break
        if time.time() - last > quiet_end + (2.0 if ended else 1e9):
            raise TimeoutError(f"no data from the board; received {len(out)} bytes, sent {sent}")
    n = n_data
    rep = P.parse_report(bytes(out[3 * n: 3 * n + P.REPORT_LEN]))
    r1, r2, r3 = P.split_words(bytes(out[:3 * n]))
    return r1, r2, r3, rep, time.time() - t0


def l2_decisions(data, ident, p, S, ebn0, seed, n_t=N_T):
    """Bit-true model of the same run: returns the three receivers' byte strings and the counters."""
    import l2_ref as R
    payload = np.unpackbits(np.concatenate([np.frombuffer(bytes(data), np.uint8), np.zeros(1, np.uint8)])).astype(np.int64)
    states = R.ff.lfsr_start_values(seed + 500000)
    sq = R.ff.sigma_q_from_ebn0(ebn0)
    ntot = P.payload_total(n_t, len(data))
    _, g, cnt = R.chain(ntot, n_t, ident["B_ACC"], ident["B_MUL"], ident["RND"], p, S, C_LO, C_HI, sq, states, payload)
    nb = 8 * len(data)
    pk = lambda v: np.packbits((v >= 0).astype(np.uint8)).tobytes()
    return (pk(g[n_t:n_t + nb, 0]), pk(g[n_t + 2:n_t + 2 + nb, 3]), pk(g[n_t + 2:n_t + 2 + nb, 2])), cnt


def frame_for(data_len, p, S, ebn0, seed, play=False, n_t=N_T, n_total=None):
    import l2_ref as R
    states = R.ff.lfsr_start_values(seed + 500000)
    sq = R.ff.sigma_q_from_ebn0(ebn0)
    ntot = P.payload_total(n_t, data_len) if n_total is None else n_total
    return P.config_frame(p, S, C_LO, C_HI, S is None, sq, n_t, ntot, 0, states, payload=True, play=play)


def bit_errors(a, b):
    x = np.frombuffer(a, np.uint8) ^ np.frombuffer(b, np.uint8)
    return int(np.unpackbits(x).sum())


def snr_db(orig, rec):
    xo = orig.astype(float) - 128; xr = np.frombuffer(rec, np.uint8).astype(float) - 128
    e = np.sum((xo - xr) ** 2)
    return float("inf") if e == 0 else float(10 * np.log10(np.sum(xo ** 2) / e))


def run_set(board, ident, data, scen, check_l2, kind):
    rows = []
    for (name, p, S, ebn0, seed) in scen:
        frame = frame_for(len(data), p, S, ebn0, seed)
        r1, r2, r3, rep, dt = stream(board, frame, data)
        row = dict(scenario=name, mu=f"2^-{p}", S=S, ebn0_db=ebn0, noise_seed=seed, bytes=len(data), board_seconds=round(dt, 2),
                   bit_errors=[bit_errors(r, data) for r in (r1, r2, r3)], bits=8 * len(data), counters_L5=rep["counters"])
        row["BER"] = [e / row["bits"] for e in row["bit_errors"]]
        if check_l2:
            dec, cnt = l2_decisions(data, ident, p, S, ebn0, seed)
            row["identical_to_L2"] = bool(dec == (r1, r2, r3) and cnt == rep["counters"])
        rows.append((row, (r1, r2, r3)))
        tag = "" if not check_l2 else f" | board == L2: {row['identical_to_L2']}"
        print(f"{kind} {name:14s} mu={row['mu']:5s} S={str(S):>5} {ebn0:4.1f} dB: bit errors R1/R2/R3 = "
              f"{row['bit_errors'][0]}/{row['bit_errors'][1]}/{row['bit_errors'][2]} of {row['bits']} ({dt:.1f} s){tag}")
    return rows


def load_clip(path, max_seconds):
    """Any audio file -> 8 kHz mono 8-bit unsigned PCM (the P5 format), cut to max_seconds. Uses ffmpeg when available
    (any format: wav, mp3, m4a, ...), otherwise reads a WAV with scipy and resamples it."""
    import shutil, subprocess, tempfile
    if shutil.which("ffmpeg"):
        tmp = os.path.join(tempfile.mkdtemp(), "clip_8k.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-t", str(max_seconds), "-ac", "1", "-ar", "8000",
                        "-acodec", "pcm_u8", tmp], check=True)
        fs, x = wavfile.read(tmp)
        return x.astype(np.uint8)
    from scipy.signal import resample_poly
    fs, x = wavfile.read(path)
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = x[: int(max_seconds * fs)]
    x = resample_poly(x - x.mean(), 8000, fs)
    x = x / max(1e-9, np.max(np.abs(x)))
    return np.clip(np.round(x * 127 + 128), 0, 255).astype(np.uint8)


def cmd_audio(board, ident, check_l2, clip=None, max_seconds=20.0):
    global OUT
    if clip:
        orig = load_clip(clip, max_seconds)
        name = os.path.splitext(os.path.basename(clip))[0]
        OUT = os.path.join(HERE, "results", "payload", "custom_" + "".join(c if c.isalnum() else "_" for c in name))
        os.makedirs(OUT, exist_ok=True)
        wavfile.write(os.path.join(OUT, "original_8k.wav"), 8000, orig)
        print(f"clip: {clip} -> {len(orig) / 8000:.1f} s at 8 kHz, 8-bit ({8 * len(orig)} bits); results in {OUT}")
    else:
        fs, orig = wavfile.read(os.path.join(P5, "audio", "p5", "original_8k.wav"))
        assert fs == 8000 and orig.dtype == np.uint8
    data = orig.tobytes()
    scen = [("static", 8, None, 14.0, 700000), ("slow_S1000", 8, 1000, 14.0, 700000),
            ("boundary_S28", 8, 28, 14.0, 700000), ("fast_S1", 8, 1, 14.0, 700000)]
    os.makedirs(OUT, exist_ok=True)
    rows = run_set(board, ident, data, scen, check_l2, "audio")
    res = []
    for row, recs in rows:
        row["waveform_SNR_dB"] = [snr_db(orig, r) for r in recs]
        for rx, r in zip(("R1", "R2", "R3"), recs):
            wavfile.write(os.path.join(OUT, f"audio_{row['scenario']}_{rx}.wav"), 8000, np.frombuffer(r, np.uint8))
        res.append(row)
        print(f"      waveform SNR R1/R2/R3 = " + " / ".join(f"{v:.1f}" for v in row["waveform_SNR_dB"]) + " dB")
    meta = dict(level="L5 measured on the Boolean Board; LFSR sum-of-uniforms noise; supervised LMS; bit-true build "
                      f"B_mul={ident['B_MUL']} B_acc={ident['B_ACC']} RND={ident['RND']}",
                payload=(f"user clip {os.path.basename(clip)}" if clip else "P5 voice recording")
                        + ", 8 kHz mono 8-bit unsigned PCM, MSB first", N_T=N_T, channel=[C_LO, C_HI],
                rows=res, date=time.strftime("%Y-%m-%d %H:%M"))
    json.dump(meta, open(os.path.join(OUT, "audio_metrics.json"), "w"), indent=1)
    return all(r.get("identical_to_L2", True) for r in res)


def p5_image():
    from skimage import color, data as skdata, transform                       # exactly as c10_image.py of the mid-term
    img = color.rgb2gray(skdata.astronaut()); h0 = int(512 * 9 / 16); top = (512 - h0) // 2
    img = transform.resize(img[top:top + h0, :], (72, 128), anti_aliasing=True)
    return np.clip(np.round(img * 255), 0, 255).astype(np.uint8)


def cmd_image(board, ident, check_l2):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    pix = p5_image()
    data = pix.tobytes()                                                       # raster order, MSB first
    scen = []
    for eb in (10.0, 12.0):
        for S in (None, 1000, 28, 5, 1):
            scen.append((f"{eb:g}dB_{'static' if S is None else 'S' + str(S)}", 8, S, eb, 700001))
    scen.append(("10dB_S1_mu2-5", 5, 1, 10.0, 700001))
    os.makedirs(OUT, exist_ok=True)
    plt.imsave(os.path.join(OUT, "image_original_128x72.png"), pix, cmap="gray", vmin=0, vmax=255)
    rows = run_set(board, ident, data, scen, check_l2, "image")
    res = []
    for row, recs in rows:
        ims = [np.frombuffer(r, np.uint8).reshape(72, 128) for r in recs]
        row["wrong_pixels"] = [int(np.sum(im != pix)) for im in ims]
        row["mean_abs_pixel_error"] = [float(np.mean(np.abs(im.astype(int) - pix.astype(int)))) for im in ims]
        for rx, im in zip(("R1", "R2", "R3"), ims):
            plt.imsave(os.path.join(OUT, f"image_{row['scenario']}_{rx}.png"), im, cmap="gray", vmin=0, vmax=255)
        res.append(row)
        print(f"      wrong pixels R1/R2/R3 = {row['wrong_pixels'][0]}/{row['wrong_pixels'][1]}/{row['wrong_pixels'][2]} of 9216")
    meta = dict(level="L5 measured on the Boolean Board; LFSR sum-of-uniforms noise; supervised LMS; bit-true build "
                      f"B_mul={ident['B_MUL']} B_acc={ident['B_ACC']} RND={ident['RND']}",
                payload="P5 image (skimage astronaut, 128x72, 8 bit), raster order, MSB first", N_T=N_T, channel=[C_LO, C_HI],
                rows=res, date=time.strftime("%Y-%m-%d %H:%M"))
    json.dump(meta, open(os.path.join(OUT, "image_metrics.json"), "w"), indent=1)
    return all(r.get("identical_to_L2", True) for r in res)


def cmd_live(board, ident, a):
    import sounddevice as sd
    os.makedirs(OUT, exist_ok=True)
    q = queue.Queue()
    sent_audio, got = bytearray(), {"R1": bytearray(), "R2": bytearray(), "R3": bytearray()}
    play_q = queue.Queue()

    def mic_cb(indata, frames, t, status):
        x = np.frombuffer(bytes(indata), np.int16)
        u8 = (np.clip((x.astype(np.int32) >> 8) + 128, 0, 255)).astype(np.uint8).tobytes()
        sent_audio.extend(u8); q.put(u8)

    pc_out = None
    if a.pc_play:
        def out_cb(outdata, frames, t, status):
            need, b = frames, bytearray()
            while len(b) < need:
                try: b += play_q.get_nowait()
                except queue.Empty: break
            if len(b) < need: b += bytes([128]) * (need - len(b))
            outdata[:] = bytes(b[:need])
        pc_out = sd.RawOutputStream(samplerate=8000, channels=1, dtype="uint8", callback=out_cb, blocksize=400)

    stats = {"t": time.time(), "n": 0}

    def on_words(out, w0, w1):
        seg = bytes(out[3 * w0: 3 * w1])
        for rx, part in zip(("R1", "R2", "R3"), P.split_words(seg)):
            got[rx] += part
        if a.pc_play:
            play_q.put(bytes(got[a.pc_play][-(w1 - w0):]))
        if time.time() - stats["t"] >= 1.0:
            n = len(got["R3"]); ref = bytes(sent_audio[:n])
            e = [bit_errors(bytes(got[rx][:n]), ref) for rx in ("R1", "R2", "R3")]
            print(f"  {n / 8000:5.1f} s of audio: bit errors so far R1/R2/R3 = {e[0]}/{e[1]}/{e[2]} (BER "
                  + " / ".join(f"{v / max(1, 8 * n):.1e}" for v in e) + ")")
            stats["t"] = time.time()

    frame = frame_for(0, a.p, a.S, a.ebn0, 900000, play=True, n_total=0)    # n_total = 0: until the stream stops
    print(f"live: {a.seconds} s, mu = 2^-{a.p}, S = {a.S}, {a.ebn0} dB; board audio jack plays the receiver chosen by SW[11:10]"
          + (f"; PC plays {a.pc_play}" if a.pc_play else ""))

    def stopper():
        time.sleep(a.seconds); q.put(None)
    mic = sd.RawInputStream(samplerate=8000, channels=1, dtype="int16", callback=mic_cb, blocksize=400)
    with mic:
        if pc_out: pc_out.start()
        threading.Thread(target=stopper, daemon=True).start()
        r1, r2, r3, rep, dt = stream(board, frame, b"", source=q, on_words=on_words)
        if pc_out: time.sleep(0.5); pc_out.stop()
    n = min(len(r3), len(sent_audio))
    orig = np.frombuffer(bytes(sent_audio[:n]), np.uint8)
    wavfile.write(os.path.join(OUT, "live_original.wav"), 8000, orig)
    res = dict(level="L5 live demonstration (microphone input, not repeatable; not a tracking measurement)",
               seconds=round(n / 8000, 2), mu=f"2^-{a.p}", S=a.S, ebn0_db=a.ebn0, counters_L5=rep["counters"])
    for rx, r in zip(("R1", "R2", "R3"), (r1, r2, r3)):
        wavfile.write(os.path.join(OUT, f"live_{rx}.wav"), 8000, np.frombuffer(r[:n], np.uint8))
        res[rx] = dict(bit_errors=bit_errors(r[:n], orig.tobytes()), BER=bit_errors(r[:n], orig.tobytes()) / max(1, 8 * n),
                       waveform_SNR_dB=snr_db(orig, r[:n]))
    json.dump(res, open(os.path.join(OUT, "live_metrics.json"), "w"), indent=1)
    print("live done:", {rx: (res[rx]["bit_errors"], round(res[rx]["waveform_SNR_dB"], 1)) for rx in ("R1", "R2", "R3")},
          f"({res['seconds']} s); WAVs in {OUT}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audio", "image", "live"])
    ap.add_argument("--port")
    ap.add_argument("--no-l2", action="store_true")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--S", type=int, default=28)
    ap.add_argument("--p", type=int, default=8)
    ap.add_argument("--ebn0", type=float, default=10.0)
    ap.add_argument("--pc-play", choices=["R1", "R2", "R3"])
    ap.add_argument("--file", help="audio: your own clip (any format ffmpeg reads) instead of the P5 recording")
    ap.add_argument("--max-seconds", type=float, default=20.0, help="audio --file: use at most this many seconds")
    a = ap.parse_args()
    b = Board(a.port or find_port())
    ident = b.ident()
    print("board:", ident)
    if ident["version"] < 2:
        raise SystemExit("the loaded bitstream has no payload transport (version < 2)")
    if a.cmd == "audio":
        ok = cmd_audio(b, ident, not a.no_l2, a.file, a.max_seconds)
    elif a.cmd == "image":
        ok = cmd_image(b, ident, not a.no_l2)
    else:
        ok = cmd_live(b, ident, a)
    print("ALL IDENTICAL TO L2" if ok and a.cmd != "live" and not a.no_l2 else "done")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
