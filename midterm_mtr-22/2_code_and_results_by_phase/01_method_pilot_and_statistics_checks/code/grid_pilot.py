"""FREEZE-1 grid pilot (L1 PILOT, pilot seeds 1000-1019): half-octave mu grid and refined S grid on the primary channel, 16 dB and 14 dB.
Run: python3 grid_pilot.py > results/grid_pilot_run_log.txt"""
import numpy as np
from sweep import *
from freeze_grids import MU_FLOAT, S_LIST, STATIC_C
CFG = dict(channel=(40, 116), snrs=[16.0, 14.0], S_list=S_LIST, mus=MU_FLOAT, seeds=list(range(1000, 1020)), static_seeds=list(range(1000, 1020)),
           static_c=STATIC_C, n_t=30000, base_eval=152000)
if __name__ == "__main__":
    import sys
    snr = float(sys.argv[1]); CFG["snrs"] = [snr]
    print("grid pilot", {k: (v if k not in ("mus",) else [round(float(np.log2(m)), 1) for m in v]) for k, v in CFG.items()})
    run_sweep(CFG, f"results/grid_pilot_raw_{snr:.0f}.npz", log=lambda s: print(s, flush=True))
