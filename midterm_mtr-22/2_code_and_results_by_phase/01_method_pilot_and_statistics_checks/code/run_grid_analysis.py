import sys
from sweep_analyse import *
from freeze_grids import *
snr = float(sys.argv[1])
cfg = dict(channel=(40,116), S_list=S_LIST, mus=MU_FLOAT, seeds=list(range(1000,1020)), static_c=STATIC_C)
lines=[]
def lg(s): print(s); lines.append(s)
analyse(f"results/grid_pilot_raw_{snr:.0f}.npz", cfg, snr, out_json=f"results/grid_pilot_analysis_{snr:.0f}.json", log=lg)
open(f"results/grid_pilot_analysis_log_{snr:.0f}.txt","w").write("\n".join(lines))
