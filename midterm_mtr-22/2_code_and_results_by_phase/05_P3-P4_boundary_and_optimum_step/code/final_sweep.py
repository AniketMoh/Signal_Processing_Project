"""FINAL L1 tracking sweep (FREEZE-1 approved 20 Oct 2026).  Configuration is read from freeze_grids.py only; nothing here may be changed
without a logged decision.  usage: python3 final_sweep.py <channel: primary|control> <EbN0_dB> [ber14]
  'ber14' = the 14 dB BER-resolution study: primary channel, mu <= 2^-7, seeds 100000-101499 (E-5).
Output: results/final_<tag>_raw.npz and results/final_<tag>_run_log.txt.  LMS loop unchanged (lms_lib.lms_receivers)."""
import sys, json, time
from sweep import run_sweep
from freeze_grids import MU_FLOAT, S_LIST, CHANNELS_FINAL, FINAL_SEEDS, BER14_SEEDS
ch, snr = sys.argv[1], float(sys.argv[2]); ber14 = len(sys.argv) > 3 and sys.argv[3] == "ber14"
(lo, hi), nodes = CHANNELS_FINAL[ch]
mus = [m for m in MU_FLOAT if m <= 2.0 ** -7 + 1e-15] if ber14 else MU_FLOAT
seeds = BER14_SEEDS if ber14 else FINAL_SEEDS
cfg = dict(channel=(lo, hi), snrs=[snr], S_list=S_LIST, mus=mus, seeds=seeds, static_seeds=seeds, static_c=nodes, n_t=30000, base_eval=152000)
tag = f"{ch}_{snr:.0f}" + ("_ber14" if ber14 else "")
logf = open(f"results/final_{tag}_run_log.txt", "w")
def log(s): print(s, flush=True); logf.write(s + "\n"); logf.flush()
log(f"FINAL sweep {tag}: channel {lo}-{hi}, nodes {nodes}, {len(mus)} mu, {len(S_LIST)} S + static, seeds {seeds[0]}-{seeds[-1]} ({len(seeds)}), N_T 30000; start {time.ctime()}")
run_sweep(cfg, f"results/final_{tag}_raw.npz", log=log)
json.dump({k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in cfg.items()}, open(f"results/final_{tag}_config.json", "w"))
log(f"done {time.ctime()}")
