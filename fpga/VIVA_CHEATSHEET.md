# Viva demo cheat sheet

## 0. Setup (before presenting)
1. Board connected with the PROG/UART USB cable, power on, all switches down.
2. Double-click **`fpga\PROGRAM_BOARD.bat`**. Accept if it prints
   `PROGRAMMED xc7s50_0 ...` and `board: {'B_MUL': 12, 'B_ACC': 16, 'RND': 1, 'version': 2}`.
   (Same thing by hand:
   `cd C:\Users\Pradeep\Signal_Processing_Project\fpga\vivado` then
   `D:\2025.2\Vivado\bin\vivado.bat -mode batch -nojournal -nolog -source program_board.tcl -tclargs bitstreams/top_boolean_m12_a16_r1.bit`)
3. Open PowerShell in the host folder for parts 2 and 3:
   `cd C:\Users\Pradeep\Signal_Processing_Project\fpga\host`

## 1. Board alone (no PC)
Switches: SW0 up (S = 5000), SW3 + SW4 up (mu = 2^-8), SW6 up (10 dB), the rest down. Press **BTN0** right before showing
(known demo-mode limit: after ~11.5 min of continuous running the 32-bit symbol counter wraps, the board silently retrains and
R2 freezes at a random channel point, so the right display can stick at 9999; BTN0 fixes it. Host-mode results are unaffected).
- RGB0 blue (training) -> green (tracking). **Left display = R3** errors (~300-380), **right display = R2** errors (~7400; with SW9 up: R1, 9999).
- Careful: on the dim display a 7 looks like a 1 (7400 is not 1400). RGB1 yellow (may look greenish when dim), red when R3 >= 1000.
- Step SW[2:0] from 1 up to 7 (faster channel): right (R2) stays ~7400, left (R3) goes 300 -> 380 -> 700 (S=28) -> 1500-1700 (S=1), RGB1 turns red.
  (Rehearsal 13 Nov: S=5000 300, S=224 380, S=28 700, S=1 1700 on the left; ~7400 on the right.)
- Say: "The frozen equaliser cannot follow the channel; the adaptive LMS one follows until the channel moves too fast."

| SW2 SW1 SW0 | S (lower = faster channel) |
|---|---|
| 0 0 1 | 5000 |
| 0 1 0 | 1000 |
| 0 1 1 | 224 |
| 1 0 0 | 112 |
| 1 0 1 | 28 |
| 1 1 0 | 5 |
| 1 1 1 | 1 |

## 2. The board is the model (~4 min)
```
python run_board.py verify
```
Accept: 8 lines `board (L5) == model (L2): True`, last line `ALL IDENTICAL`.
Say: "Every counter on the board equals our bit-true Python model; not one bit differs over millions of symbols."

## 3. Our own song through the board
```
python run_payload.py audio --file "C:\Users\Pradeep\OneDrive\Desktop\saiyara.mpeg"
```
Accept: 4 scenario lines ending `board == L2: True`, last line `ALL IDENTICAL TO L2`.
Then play from `fpga\host\results\payload\custom_saiyara\`:
`original_8k.wav`, then `audio_fast_S1_R1.wav`, `_R2.wav`, `_R3.wav` (R1 ruined, R2 noisy, R3 close to the original).

Other demos: `python run_payload.py image` (image, 11 scenarios), `python run_payload.py audio` (mid-term voice recording).

## Live screens on the laptop (run from fpga\host; close the window when done, it holds the board's port)
- **A. Tracking curve, measured live:** `python live_sweep.py` (~10 s; BER vs S point by point; R3 rises from ~3.7e-4 at
  S = 5000 to ~1.6e-3 at S = 1, R2 flat ~7e-3, R1 flat ~5e-2). Compare step sizes: `python live_sweep.py --mus 6 8 10`.
- **B. Image decoded live:** `python live_payload.py image` (~3 min; original | R1 | R2 | R3 fill in row by row,
  11 scenarios, each ticked "board == model").
- **C. Song meters:** `python live_payload.py audio --file "C:\Users\Pradeep\OneDrive\Desktop\saiyara.mpeg"`
  (~2 min; live bit-error bars and SNR, 4 scenarios, each ticked "board == model").
  **With sound (demo version):** add `--play --jack --volume 0.5`: real time (~2.5 min). Laptop speakers: the on-screen
  **R1 / R2 / R3 buttons** (or keys 1/2/3) choose what you hear, the waveform follows. Board jack: **SW10 = R2, SW11 = R1**,
  both down = R3. 13 Nov: 4/4 board == model with both outputs on.
- **D. Live microphone with graphs:** `python live_payload.py live` (30 s, S = 1000, 14 dB, earbuds' mic, gain 4;
  options `--seconds --S --ebn0 --play`). Bars, SNR and waveform update as you talk; board jack plays SW10/SW11 choice.

**Demo order:** B image -> C song with `--play --jack` -> D live microphone with graphs.

## Extra control experiment: what equalisation buys you (not a PPR tracking scenario)
`python run_board.py static-max` (~1 min): channel held still, at a = 0.31 and at the harshest a = 0.906, checked vs model.
Board 13 Nov (10 dB): a = 0.31: R1 0.10 %, R2/R3 0.00 %;  a = 0.906: **R1 17.6 %**, R2 0.15 %, R3 0.24 %.
Say: "Even on a channel that does not move, a harsh channel closes the eye: without an equaliser 1 bit in 6 is wrong;
with one it is about 1 in 500."

## Board audio jack and live microphone (headphones in the board's jack)
- Jack check, clean (0 bit errors):
  `python run_payload.py live --file "C:\Users\Pradeep\OneDrive\Desktop\saiyara.mpeg" --seconds 30 --volume 0.25 --S 0 --ebn0 20`
- Song R1/R2/R3 on the jack: same command with `--S 28 --ebn0 14` (R3 ~17 bit errors in 30 s, sounds clean).
- Live voice (earbuds' mic): `python run_payload.py live --seconds 30 --S 1000 --ebn0 14 --mic "Headset (OnePlus" --gain 4`
  (13 Nov: R3 2 bit errors in 30 s). Flip SW10 (R2) / SW11 (R1) while talking; both down = R3.
- On the board during live runs: LED13 host, LED12 payload, LED14 tracking; displays = errors per ~1 s
  (left R3, right R2, or R1 with SW9 up); RGB0 green + red (playing) looks yellowish.

## If something goes wrong
- `version: 1` or no answer: power-cycle the board, run PROGRAM_BOARD.bat again.
- `serial problem ... repeating the run`: harmless, the script retries.
- Backup: show the saved results in `fpga\host\results\` and the final report.
