"""PROPOSED frozen grids (FREEZE-1 proposal, awaiting owner confirmation).  Single source for pilot and final runs."""
import numpy as np
# half-octave mu grid for the floating-point optimum-step-size / exponent study: 2^-5 ... 2^-11.5 (14 values)
MU_FLOAT = [2.0 ** -(5 + 0.5 * j) for j in range(14)]
# powers of two kept for the FPGA-oriented comparisons (subset of the grid above): 2^-5 ... 2^-11
MU_FPGA = [2.0 ** -k for k in range(5, 12)]
# S = symbols per coefficient step (large S = slow).  Slow control rates, ~sqrt(2) spacing between 10 and 224, fast end.
S_LIST = [5000, 2000, 1000, 500, 320, 224, 160, 112, 80, 56, 40, 28, 20, 14, 10, 5, 2, 1]
# static-channel values for the trajectory-averaged baseline (counter values; linear interpolation in c)
STATIC_C = [40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 116]

# control (mild) channel, counters 26..77 (a = 0.2031 ... 0.6016), approved for the final sweep (E-4); static nodes every 8 counts + the end point
STATIC_C_CONTROL = [26, 34, 42, 50, 58, 66, 74, 77]
CHANNELS_FINAL = {"primary": ((40, 116), STATIC_C), "control": ((26, 77), STATIC_C_CONTROL)}
FINAL_SEEDS = list(range(2000, 2100))            # final tracking sweep (never used so far)
BER14_SEEDS = list(range(100000, 101500))        # 14 dB BER-resolution study, 1500 seeds (E-5)
