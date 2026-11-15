# Live mode: run the LMS equaliser demo on the Boolean Board

This page is for someone opening the project for the first time. It shows how to run the live demonstration and how to read what it shows.

The board receives a stream of bits sent over a changing channel with noise. Three receivers decode it at the same time:

| Receiver | What it is | Display |
|---|---|---|
| **R1** | no equaliser | left display with SW9 up |
| **R2** | equaliser trained once, then frozen | left display |
| **R3** | adaptive LMS equaliser (keeps learning) | right display |

The displays count bit errors per window of 2^20 symbols (about 0.17 s), roughly the BER in parts per million. 9999 means the count is off the scale.

## What you need

- A Real Digital **Boolean Board** (Spartan-7 XC7S50), connected to the PC by USB.
- **Vivado** (2025.2 was used; only the free Lab/hardware manager part is needed to program the board).
- **Python 3** with the packages in `fpga/host/requirements.txt`. Install them once:

  ```
  python -m pip install -r fpga/host/requirements.txt
  ```

- Optional: headphones in the board's audio jack, and a microphone for the live-voice demo.

## The two commands

From the repository folder:

**1. Load the design onto the board** (needed after every power-on; about 1 minute):

```
fpga\PROGRAM_BOARD.bat
```

It ends with `board: {'B_MUL': 12, 'B_ACC': 16, 'RND': 1, 'version': 2}`. If Vivado is not in `D:\2025.2\Vivado\bin`, set it first: `set VIVADO_BIN=C:\path\to\Vivado\bin`.

**2. Start a live dashboard on the PC:**

```
cd fpga\host
python live_sweep.py
```

This plots the BER of R1/R2/R3 against the channel speed, point by point, as the board measures it. Close the window to stop.

The board's own switch demo (next section) needs only command 1. The PC is not involved.

## Other live dashboards

Run these from `fpga\host`. Only one can use the board at a time, so close a window before starting the next.

| Command | Shows |
|---|---|
| `python live_sweep.py --mus 6 8 10` | tracking curve for three step sizes μ = 2⁻⁶, 2⁻⁸, 2⁻¹⁰ |
| `python live_payload.py image` | a 128×72 image filling in row by row as decoded by R1, R2 and R3 |
| `python live_payload.py audio --play` | a recorded voice clip; keys 1/2/3 switch the PC speakers between R1/R2/R3 |
| `python live_payload.py live --gain 3` | your microphone through the board, with live graphs; recordings saved in `results/live/mic_<date_time>/` |

After each scenario the board's output is checked bit by bit against the simulation model and ticked on screen. Add `--port COM8` if the board's serial port is not found automatically.

## Board switch demo (no PC needed)

After command 1, the board runs on its own. Set the switches, press **BTN0** to retrain, and wait for **RGB0 to turn green** (tracking).

| Switch | Sets |
|---|---|
| SW2–SW0 | channel speed: 0 still, 1: S = 5000, 2: 1000, 3: 224, 4: 112, 5: 28, 6: 5, 7: 1 (symbols per channel step; smaller = faster) |
| SW5–SW3 | step size μ = 2^-(5+value); value 3 gives the standard μ = 2⁻⁸ |
| SW7–SW6 | noise: 0 = 8 dB, 1 = 10 dB, 2 = 12 dB, 3 = 14 dB |
| SW8 | 0 primary channel, 1 milder control channel (a change retrains) |
| SW9 | left display shows R1 instead of R2 |
| SW12 | hold the channel still at its harshest point, a = 0.906 (a change retrains) |
| BTN0 / BTN1 / BTN3 | retrain / clear counters / reset |

RGB1 shows R3's state: green under 100 errors per window, yellow 100–999, red 1000 or more.

### Expected readings (μ = 2⁻⁸: SW3 and SW4 up; 10 dB: SW6 up)

Measured on the board (L5) on 13–14 Nov 2026, primary channel, 10 dB:

| Channel | R1 | R2 (left) | R3 (right) |
|---|---|---|---|
| still at a = 0.906 (SW12) | 9999 | 1700 | 2500 |
| S = 5000 (10 dB) | 9999 | ~7400 | ~300 |
| S = 224 | 9999 | ~7400 | ~380 |
| S = 28 | 9999 | ~7400 | ~700 |
| S = 1 | 9999 | ~7400 | 1500–1700 |

The numbers move a little from window to window because the noise is random.

## What the live mode shows

**1. Adapting wins when the channel moves.** On a moving channel the frozen R2 makes about 20× more errors than R3, because its weights describe a channel that no longer exists. R3 degrades slowly as the channel speeds up (300 → 1700). That growth is the tracking limit the project measures: the faster the channel, the more symbols per step (S\*) LMS needs to keep up.

**2. On a still channel the frozen filter is better (SW12).** With SW12, R2 (1700) beats R3 (2500). This is expected, not a fault:
- R2's weights were frozen at the optimum.
- R3 keeps updating, and every update adds a little noise to its weights. That cost is the excess error called misadjustment.
- The report measures it at 1.47× the error of the optimal filter and predicts it from theory (1.468).
- Adapting pays only when the channel changes faster than this cost.

**3. A frozen filter does not need to follow the noise level.** The noise switches act immediately and do **not** retrain. What to expect:
- Raising the noise makes every receiver worse, because no filter can remove white noise.
- The best weights depend mainly on the channel and only weakly on the noise at 8–14 dB, so a frozen R2 trained at another noise level should lose very little.
- To check it: SW12 on, 10 dB, BTN0, note the readings; flip to 8 dB without BTN0, note them; press BTN0 and note again. If the last two readings agree, the old weights were already right.
- *Status: prediction, not yet measured on the board.*

**4. Too large a step size fails.** With μ = 2⁻⁵ (SW5–SW3 all down) R3 is noisy even on a slow channel: large steps track fast but jitter a lot.

**Where the numbers come from:**
- Board vs model checks: `fpga/FPGA_RESULTS.md`.
- Re-measurement of the mid-term findings on the board: `fpga/host/results/confirm/CONFIRMATION_REPORT.md`.
- Full discussion: §7.5–7.6 of the final report (`final_report/s_fpga.tex`).

## Limits and next steps

**What this study does not model.** The signal is real-valued BPSK at baseband, so the **carrier phase rotation** that a moving platform causes is absent. An underwater link at 12 kHz and 2 ksymbol/s would rotate by 1.4° per symbol at 1 m/s, one full turn every 250 symbols. Adding it would bring in:
- **New parameters:** carrier frequency and platform speed (the Doppler shift), starting phase, phase noise; on the receiver, complex LMS taps and a phase-locked loop (loop gains or bandwidth, and damping). The PLL bandwidth then has to be balanced against μ.
- **What to expect** (not measured):
  - R1 and R2 would fail completely, since BPSK flips sign every half turn.
  - LMS alone would hold on only with a large μ.
  - LMS with a PLL would keep a small μ and clean output.
- **Hardware cost:** about four times the multipliers. The current design uses 51 of the 120 DSP blocks, so the complex filter would have to be time-shared.

**Improvements within the current study:**

| Improvement | Why |
|---|---|
| Measure the noise-change test above on the board | turns point 3 from a prediction into a result |
| More seeds at μ = 2⁻⁷ and 2⁻⁸, 14 dB | the board still gives only a bracket for S\*_BER at these two points |
| More Gaussian noise generator (more uniforms summed, or Box–Muller) | the sum-of-uniforms noise has light tails; it is the only reason the board's BER is lower than the simulation's below about 10⁻⁴ |
| Variable step size (large μ while the error is large, small once settled) | reduces the misadjustment that lets R2 beat R3 on still channels |
| Shorter training (large μ first, then smaller) | the demo now trains on 30 000 symbols after each BTN0 |
| Decision-feedback equaliser, RLS, longer random multipath, deep fades, error-correcting coding | future work, listed in the report's conclusion |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `version: 1` or no answer after command 1 | power-cycle the board and run command 1 again |
| "could not find the board" / port busy | close any open dashboard window (it holds the USB link), or pass `--port COMx` |
| displays frozen or odd after a long run | press BTN0 (retrain) or BTN1 (clear counters) |
| no sound on the jack | payload mode only; SW10/SW11 choose R2/R1, both down = R3 |
