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

## If something goes wrong
- `version: 1` or no answer: power-cycle the board, run PROGRAM_BOARD.bat again.
- `serial problem ... repeating the run`: harmless, the script retries.
- Backup: show the saved results in `fpga\host\results\` and the final report.
