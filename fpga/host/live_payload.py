# live_payload.py -- live screens for the viva while image / audio payloads go through the Boolean Board (level L5):
#   python live_payload.py image                 the P5 128x72 image fills in row by row for original | R1 | R2 | R3
#   python live_payload.py audio --file clip     live R1/R2/R3 bit-error bars and running waveform SNR for your clip
#   python live_payload.py live                  microphone through the board, live graphs; board jack plays SW10/SW11
# After each scenario the board's decisions are checked against the bit-true model (L2) and ticked on screen.
# Same scenarios, frames and seeds as run_payload.py; display only, nothing is written to results/payload.
# Options: --port COMx, --no-l2 (skip the model check), --rate B/s (pace the stream so the image fills in visibly),
#          audio: --max-seconds (default 20), --save (write the final screen to results/live/),
#          --play (real time; the chosen receiver on the PC speakers, keys 1/2/3 = R1/R2/R3), --volume, --out
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
import argparse, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import protocol as P
import run_payload as RP
from run_board import Board, find_port, RESULTS

RX = ("R1", "R2", "R3")
COL = {"R1": "#9e9e9e", "R2": "#e8710a", "R3": "#1a73e8"}
NAMES = {"R1": "R1  no equaliser", "R2": "R2  frozen", "R3": "R3  adaptive LMS"}


def scen_label(name, p, S, eb):
    return f"{eb:g} dB, " + ("static channel" if S is None else f"S = {S}") + f", μ = 2^-{p}"


def run_scenarios(b, ident, data, scen, a, screen):
    """Stream every scenario with a live callback, then check against L2. screen: object with start/update/done."""
    results = []
    for k, (name, p, S, eb, seed) in enumerate(scen):
        if not plt.fignum_exists(screen.fig.number):
            break
        screen.start(k, name, p, S, eb)
        got = {rx: bytearray() for rx in RX}
        last = [0.0]

        def on_words(out, w0, w1):
            w1 = min(w1, len(data))                    # words past the payload are the final report, not data
            if w1 <= w0:
                return
            for rx, part in zip(RX, P.split_words(bytes(out[3 * w0: 3 * w1]))):
                got[rx] += part
            if time.time() - last[0] > 0.15:
                screen.update(got); last[0] = time.time()

        frame = RP.frame_for(len(data), p, S, eb, seed, play=getattr(a, "jack", False))
        for attempt in range(3):         # a new frame restarts the run from the same seeds, so a repeat gives the same result
            try:
                r1, r2, r3, rep, dt = RP.stream(b, frame, data, rate=a.rate, on_words=on_words)
                break
            except (TimeoutError, ValueError) as e:
                print(f"  serial problem ({e}); repeating the scenario ({attempt + 1}/3)")
                if attempt == 2:
                    raise
                b.reopen(); time.sleep(0.5)
                for rx in RX:
                    got[rx].clear()
        got = {"R1": bytearray(r1), "R2": bytearray(r2), "R3": bytearray(r3)}
        screen.update(got)
        if hasattr(screen, "wait_played"):
            screen.wait_played()
        ok = None
        if not a.no_l2:
            screen.checking(k)
            dec, cnt = RP.l2_decisions(data, ident, p, S, eb, seed)
            ok = bool(dec == (r1, r2, r3) and cnt == rep["counters"])
        errs = [RP.bit_errors(r, data) for r in (r1, r2, r3)]
        screen.done(k, ok, errs)
        print(f"{name:14s}: bit errors R1/R2/R3 = {errs[0]}/{errs[1]}/{errs[2]} of {8 * len(data)}"
              + ("" if ok is None else f" | board == L2: {ok}"))
        results.append(ok)
    return results


class ImageScreen:
    def __init__(self, pix, scen):
        self.pix, self.scen = pix, scen
        self.fig = plt.figure(figsize=(13, 6.2))
        self.fig.canvas.manager.set_window_title("Live image through the Boolean Board (L5)")
        gs = self.fig.add_gridspec(2, 4, height_ratios=[3.2, 1.4])
        self.axs = [self.fig.add_subplot(gs[0, i]) for i in range(4)]
        self.ims = []
        for i, ax in enumerate(self.axs):
            ax.set_xticks([]); ax.set_yticks([])
            self.ims.append(ax.imshow(pix if i == 0 else np.full_like(pix, 0), cmap="gray", vmin=0, vmax=255))
        self.axs[0].set_title("original (sent)", fontsize=11)
        self.tab = self.fig.add_subplot(gs[1, :]); self.tab.axis("off")
        self.lines = []
        for k, (name, p, S, eb, _) in enumerate(scen):
            col, row = divmod(k, 6)
            t = self.tab.text(0.01 + 0.5 * col, 0.92 - 0.17 * row, "  " + scen_label(name, p, S, eb), fontsize=9.5,
                              family="monospace", color="#777", transform=self.tab.transAxes, va="top")
            self.lines.append(t)
        self.sup = self.fig.suptitle("", fontsize=13)
        self.fig.tight_layout(rect=(0, 0, 1, 0.95)); plt.pause(0.05)

    def start(self, k, name, p, S, eb):
        self.k = k
        self.sup.set_text(f"Image through the FPGA, live:  {scen_label(name, p, S, eb)}   (scenario {k + 1}/{len(self.scen)})")
        for i in range(1, 4):
            self.ims[i].set_data(np.full_like(self.pix, 0))
        self.lines[k].set_color("#000"); self.lines[k].set_text("▶ " + self.lines[k].get_text()[2:])
        self.update({rx: b"" for rx in RX})

    def update(self, got):
        flat = self.pix.reshape(-1)
        for i, rx in enumerate(RX, start=1):
            n = len(got[rx])
            im = np.zeros(flat.size, np.uint8); im[:n] = np.frombuffer(bytes(got[rx]), np.uint8)
            self.ims[i].set_data(im.reshape(self.pix.shape))
            e = RP.bit_errors(bytes(got[rx]), flat[:n].tobytes()) if n else 0
            wp = int(np.sum(im[:n] != flat[:n]))
            self.axs[i].set_title(f"{NAMES[rx]}\nbit errors {e}   wrong pixels {wp}", fontsize=10, color=COL[rx])
        self.fig.canvas.draw_idle(); plt.pause(0.001)

    def checking(self, k):
        self.lines[k].set_text(self.lines[k].get_text() + "   checking against the model ..."); plt.pause(0.01)

    def done(self, k, ok, errs):
        base = "  " + self.lines[k].get_text()[2:].split("   checking")[0]
        mark = "" if ok is None else ("   board == model ✔" if ok else "   board != model ✘")
        self.lines[k].set_text(base + f"   R1/R2/R3 {errs[0]}/{errs[1]}/{errs[2]}" + mark)
        self.lines[k].set_color("#0b8043" if ok else ("#000" if ok is None else "#c5221f"))
        self.fig.canvas.draw_idle(); plt.pause(0.01)


class AudioScreen:
    """Bit-error bars, SNR bars, a scrolling waveform (original vs the receiver being heard) and, with play=True, the chosen
    receiver's decoded audio on the PC output as it comes back from the board (keys 1/2/3 switch R1/R2/R3)."""

    def __init__(self, orig, scen, title, play=False, out=None, volume=1.0):
        self.orig, self.scen, self.title = orig, scen, title
        self.sel, self.cur, self.pos, self.volume = "R3", {rx: bytearray() for rx in RX}, 0, volume
        self.stream = None
        self.jack_hint = ""
        self.fig = plt.figure(figsize=(13, 7.6))
        self.fig.canvas.manager.set_window_title("Live audio through the Boolean Board (L5)")
        gs = self.fig.add_gridspec(3, 2, height_ratios=[2.6, 1.5, 1.2])
        self.ax_e = self.fig.add_subplot(gs[0, 0]); self.ax_s = self.fig.add_subplot(gs[0, 1])
        self.bars_e = self.ax_e.bar(RX, [1, 1, 1], color=[COL[r] for r in RX])
        self.ax_e.set_yscale("log"); self.ax_e.set_ylim(0.8, 2e5); self.ax_e.set_title("bit errors so far (log scale)")
        self.bars_s = self.ax_s.bar(RX, [0, 0, 0], color=[COL[r] for r in RX])
        self.ax_s.set_ylim(-20, 60); self.ax_s.axhline(0, color="#555", lw=0.8)
        self.ax_s.set_title("waveform SNR so far (dB, higher = cleaner)")
        self.txt_e = [self.ax_e.text(i, 1, "", ha="center", va="bottom", fontsize=11) for i in range(3)]
        self.txt_s = [self.ax_s.text(i, 0, "", ha="center", va="bottom", fontsize=11) for i in range(3)]
        self.ax_w = self.fig.add_subplot(gs[1, :])
        self.ax_w.set_ylim(-130, 130); self.ax_w.set_yticks([]); self.ax_w.set_xticks([])
        self.w_orig, = self.ax_w.plot([], [], color="#bbb", lw=1.0, label="original")
        self.w_rx, = self.ax_w.plot([], [], color=COL["R3"], lw=1.0, label="R3")
        self.ax_w.legend(loc="upper right", fontsize=9)
        self.tab = self.fig.add_subplot(gs[2, :]); self.tab.axis("off")
        self.lines = [self.tab.text(0.01, 0.95 - 0.24 * k, "  " + scen_label(n, p, S, eb), fontsize=10, family="monospace",
                                    color="#777", transform=self.tab.transAxes, va="top")
                      for k, (n, p, S, eb, _) in enumerate(scen)]
        self.sup = self.fig.suptitle("", fontsize=13)
        self.fig.canvas.mpl_connect("key_press_event", self.on_key)
        from matplotlib.widgets import Button
        self.buttons = []
        for i, rx in enumerate(RX):
            bax = self.fig.add_axes([0.80 + 0.065 * i, 0.005, 0.06, 0.045])
            btn = Button(bax, rx, color=COL[rx], hovercolor="#ddd")
            btn.label.set_color("white"); btn.label.set_fontweight("bold")
            btn.on_clicked(lambda ev, k=i: self.select(RX[k]))
            self.buttons.append(btn)
        if play:
            import sounddevice as sd
            dev = RP.pick_device(sd, out, "out") if out else None
            self.stream = sd.RawOutputStream(samplerate=8000, channels=1, dtype="uint8", blocksize=400, device=dev,
                                             callback=self.audio_cb)
            self.stream.start()
        self.set_wtitle()
        self.fig.tight_layout(rect=(0, 0, 1, 0.95)); plt.pause(0.05)

    def audio_cb(self, outdata, frames, t, status):
        buf = self.cur[self.sel]
        if self.pos + frames <= len(buf):
            x = np.frombuffer(bytes(buf[self.pos:self.pos + frames]), np.uint8).astype(np.float64) - 128
            outdata[:] = np.clip(np.round(128 + self.volume * x), 0, 255).astype(np.uint8).tobytes()
            self.pos += frames
        else:
            outdata[:] = bytes([128]) * frames                     # waiting for the board: silence

    def on_key(self, ev):
        if ev.key in ("1", "2", "3"):
            self.select(RX[int(ev.key) - 1])

    def select(self, rx):
        self.sel = rx
        self.w_rx.set_color(COL[rx]); self.w_rx.set_label(rx)
        self.ax_w.legend(loc="upper right", fontsize=9)
        self.set_wtitle(); self.fig.canvas.draw_idle()

    def set_wtitle(self):
        hint = "   (buttons below or keys 1 / 2 / 3: R1 / R2 / R3)" + (self.jack_hint if self.jack_hint else "")
        self.ax_w.set_title(f"waveform: original (grey) and {NAMES[self.sel]}" + ("  -- now playing" if self.stream else "")
                            + hint, fontsize=10, color=COL[self.sel])

    def start(self, k, name, p, S, eb):
        self.cur, self.pos = {rx: bytearray() for rx in RX}, 0
        self.sup.set_text(f"{self.title}:  {scen_label(name, p, S, eb)}   (scenario {k + 1}/{len(self.scen)})")
        self.lines[k].set_color("#000"); self.lines[k].set_text("▶ " + self.lines[k].get_text()[2:])
        self.update(self.cur)

    def update(self, got):
        self.cur = got                                             # the audio callback reads the receiver bytes from here
        n = len(got["R3"])
        for i, rx in enumerate(RX):
            m = min(n, len(got[rx]), len(self.orig))
            e = RP.bit_errors(bytes(got[rx][:m]), self.orig[:m].tobytes()) if m else 0
            s = RP.snr_db(self.orig[:m], bytes(got[rx][:m])) if m else 0.0
            s_show = 60.0 if not np.isfinite(s) else max(-20.0, min(60.0, s))
            self.bars_e[i].set_height(max(e, 0.8)); self.txt_e[i].set_position((i, max(e, 0.8))); self.txt_e[i].set_text(f"{e}")
            self.bars_s[i].set_height(s_show); self.txt_s[i].set_position((i, max(s_show, 0)))
            self.txt_s[i].set_text("perfect" if not np.isfinite(s) else f"{s:.1f}")
        # waveform: the last 0.25 s heard (or the newest samples when not playing)
        end = min(self.pos if self.stream else n, len(got[self.sel]), len(self.orig))
        a0 = max(0, end - 2000)
        if end > a0:
            t = np.arange(a0, end) / 8000
            self.w_orig.set_data(t, self.orig[a0:end].astype(int) - 128)
            self.w_rx.set_data(t, np.frombuffer(bytes(got[self.sel][a0:end]), np.uint8).astype(int) - 128)
            self.ax_w.set_xlim(t[0], t[0] + 0.25)
        self.ax_e.set_xlabel(f"{n / 8000:.1f} s of audio received" if n else "")
        self.fig.canvas.draw_idle(); plt.pause(0.001)

    def wait_played(self):
        """With playback: let the chosen receiver finish playing before the model check and the next scenario."""
        while self.stream and self.pos + 400 < len(self.cur[self.sel]) and plt.fignum_exists(self.fig.number):
            self.update(self.cur); plt.pause(0.1)

    checking = ImageScreen.checking
    done = ImageScreen.done



def run_live(b, a):
    """Microphone -> board in real time; the board jack plays the receiver chosen by SW10/SW11; live graphs on screen.
    A demonstration (not repeatable), not a measurement: no model check."""
    import queue, threading
    import sounddevice as sd
    mic_dev = RP.pick_device(sd, a.mic, "in")
    print("microphone:", sd.query_devices(mic_dev)["name"])
    q, sent = queue.Queue(), bytearray()

    def mic_cb(indata, frames, t, status):
        x = np.frombuffer(bytes(indata), np.int16)
        u8 = np.clip(np.round(x.astype(np.float64) * a.gain / 256) + 128, 0, 255).astype(np.uint8).tobytes()
        sent.extend(u8); q.put(u8)

    S = a.S or None
    scen = [("live", a.p, S, a.ebn0, 0)]
    screen = AudioScreen(np.zeros(0, np.uint8), scen, f"Live microphone through the FPGA ({a.seconds:g} s)",
                         play=a.play, out=a.out, volume=a.volume)
    screen.jack_hint = "   | board jack: SW10 = R2, SW11 = R1, both down = R3"
    screen.start(0, "live", a.p, S, a.ebn0)
    got, last = {rx: bytearray() for rx in RX}, [0.0]

    def on_words(out, w0, w1):
        for rx, part in zip(RX, P.split_words(bytes(out[3 * w0: 3 * w1]))):
            got[rx] += part
        if time.time() - last[0] > 0.15:
            screen.orig = np.frombuffer(bytes(sent), np.uint8)
            screen.update(got); last[0] = time.time()

    frame = RP.frame_for(0, a.p, S, a.ebn0, 900000, play=True, n_total=0)
    mic = sd.RawInputStream(samplerate=8000, channels=1, dtype="int16", callback=mic_cb, blocksize=400, device=mic_dev)
    with mic:
        threading.Thread(target=lambda: (time.sleep(a.seconds), q.put(None)), daemon=True).start()
        r1, r2, r3, rep_, dt = RP.stream(b, frame, b"", source=q, on_words=on_words)
    n = min(len(r3), len(sent))
    screen.orig = np.frombuffer(bytes(sent[:n]), np.uint8)
    final = {"R1": bytearray(r1[:n]), "R2": bytearray(r2[:n]), "R3": bytearray(r3[:n])}
    screen.update(final)
    if hasattr(screen, "wait_played"):
        screen.wait_played()
    errs = [RP.bit_errors(bytes(final[rx]), screen.orig.tobytes()) for rx in RX]
    screen.done(0, None, errs)
    screen.sup.set_text(f"Live microphone through the FPGA: {n / 8000:.1f} s, bit errors R1/R2/R3 = "
                        f"{errs[0]}/{errs[1]}/{errs[2]}  (demonstration, not repeatable)")
    print(f"live: {n / 8000:.1f} s, bit errors R1/R2/R3 = {errs[0]}/{errs[1]}/{errs[2]}")
    from scipy.io import wavfile                                   # recordings: what was sent and what each receiver decoded
    out_dir = os.path.join(RESULTS, "live", "mic_" + time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    wavfile.write(os.path.join(out_dir, "original.wav"), 8000, screen.orig)
    for rx in RX:
        wavfile.write(os.path.join(out_dir, f"{rx}.wav"), 8000, np.frombuffer(bytes(final[rx]), np.uint8))
    print("recordings in", out_dir)
    if a.save:
        os.makedirs(os.path.join(RESULTS, "live"), exist_ok=True)
        screen.fig.savefig(os.path.join(RESULTS, "live", "live_mic.png"), dpi=130)
    plt.ioff(); plt.show()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["image", "audio", "live"])
    ap.add_argument("--port")
    ap.add_argument("--no-l2", action="store_true")
    ap.add_argument("--rate", type=float, default=None, help="bytes per second (image default 1500, audio: full speed)")
    ap.add_argument("--file", help="audio: your clip (default: the P5 voice recording)")
    ap.add_argument("--max-seconds", type=float, default=20.0)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--play", action="store_true", help="audio: real time, play the receiver on the PC (keys 1/2/3)")
    ap.add_argument("--out", default="", help="audio --play: output device name (part); default = Windows default")
    ap.add_argument("--volume", type=float, default=1.0, help="audio --play: playback volume scale")
    ap.add_argument("--jack", action="store_true", help="audio: also play on the board's jack (SW10/SW11 choose R2/R1)")
    ap.add_argument("--seconds", type=float, default=30.0, help="live: length")
    ap.add_argument("--S", type=int, default=1000, help="live: variation rate (0 = static)")
    ap.add_argument("--p", type=int, default=8, help="live: mu = 2^-p")
    ap.add_argument("--ebn0", type=float, default=14.0, help="live: Eb/N0 in dB")
    ap.add_argument("--mic", default="Headset (OnePlus", help="live: input device name (part)")
    ap.add_argument("--gain", type=float, default=4.0, help="live: microphone gain")
    a = ap.parse_args()
    b = Board(a.port or find_port())
    ident = b.ident()
    print("board:", ident)
    if ident["version"] < 2:
        raise SystemExit("the loaded bitstream has no payload transport (version < 2)")
    plt.ion()
    if a.cmd == "live":
        return run_live(b, a)
    if a.cmd == "image":
        if a.rate is None:
            a.rate = 1500.0
        pix = RP.p5_image()
        scen = [(f"{eb:g}dB_{'static' if S is None else 'S' + str(S)}", 8, S, eb, 700001)
                for eb in (10.0, 12.0) for S in (None, 1000, 28, 5, 1)] + [("10dB_S1_mu2-5", 5, 1, 10.0, 700001)]
        screen = ImageScreen(pix, scen)
        res = run_scenarios(b, ident, pix.tobytes(), scen, a, screen)
    else:
        if a.file:
            orig = RP.load_clip(a.file, a.max_seconds); title = f"{os.path.basename(a.file)} through the FPGA, live"
        else:
            from scipy.io import wavfile
            _, orig = wavfile.read(os.path.join(RP.P5, "audio", "p5", "original_8k.wav")); title = "P5 voice through the FPGA, live"
        scen = [("static", 8, None, 14.0, 700000), ("slow_S1000", 8, 1000, 14.0, 700000),
                ("boundary_S28", 8, 28, 14.0, 700000), ("fast_S1", 8, 1, 14.0, 700000)]
        if (a.play or a.jack) and a.rate is None:
            a.rate = 8000.0                                        # real time: 8000 bytes (samples) per second
        screen = AudioScreen(orig, scen, title, play=a.play, out=a.out, volume=a.volume)
        if a.jack:
            screen.jack_hint = "   | board jack: SW10 = R2, SW11 = R1, both down = R3"; screen.set_wtitle()
        res = run_scenarios(b, ident, orig.tobytes(), scen, a, screen)
    if res and not a.no_l2:
        allok = all(res) and len(res) == len(scen)
        screen.sup.set_text(screen.sup.get_text().split(":")[0] + (":  ALL IDENTICAL TO THE MODEL ✔" if allok
                                                                   else ":  finished"))
        print("ALL IDENTICAL TO L2" if allok else "finished")
    if a.save:
        os.makedirs(os.path.join(RESULTS, "live"), exist_ok=True)
        out = os.path.join(RESULTS, "live", f"live_{a.cmd}.png"); screen.fig.savefig(out, dpi=130); print("saved", out)
    plt.ioff(); plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
