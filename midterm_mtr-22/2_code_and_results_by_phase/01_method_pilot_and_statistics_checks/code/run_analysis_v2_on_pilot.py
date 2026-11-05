"""Re-analysis of the EXISTING grid-pilot data (L1 pilot, seeds 1000-1019; no new simulation) with sweep_analyse v2:
paired seed-bootstrap BER statuses, S_cross fix, log-linear reference, exponent sensitivity.  usage: python3 run_analysis_v2_on_pilot.py <snr>"""
import sys
from sweep_analyse import analyse
from freeze_grids import MU_FLOAT, S_LIST, STATIC_C
snr = float(sys.argv[1]); lines = []
cfg = dict(channel=(40, 116), S_list=S_LIST, mus=MU_FLOAT, seeds=list(range(1000, 1020)), static_seeds=list(range(1000, 1020)), static_c=STATIC_C)
def lg(s): print(s); lines.append(s)
analyse(f"results/grid_pilot_raw_{snr:.0f}.npz", cfg, snr, out_json=f"results/grid_pilot_analysis_v2_{snr:.0f}.json", log=lg)
open(f"results/grid_pilot_analysis_v2_log_{snr:.0f}.txt", "w").write("\n".join(lines))
