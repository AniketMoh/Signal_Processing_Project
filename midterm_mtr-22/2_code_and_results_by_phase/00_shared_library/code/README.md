# EE2000 mid-term code package — team 22

Python 3 (numpy, scipy, numba, matplotlib, scikit-image) and Verilog (iverilog / verilator).
Levels: L1 floating point, L2 bit-true fixed point, L3 RTL simulation.
Every number in the report `mtr-22.pdf` is produced by a script here; logs and figures are in `results/`.

> **Package layout.** In the submitted zip the files are grouped by phase (`2_code_and_results_by_phase/`). The paths in this README (`results/...`, `replication/...`) are the *runnable* layout the scripts expect; `manifest.csv` maps every file between the two, and `python3 make_runnable_copy.py` rebuilds the runnable layout in `runnable_code/`.

| Report section | Scripts | Outputs |
|---|---|---|
| 2 method: noise generator, integer front end | `config.py`, `fxp_front.py`, `check_front_equiv.py` | `rtl/front_equiv_log.txt` |
| 4 replications R1-R7 | `replication/rep*.py` (R5: `rep5c_ghanassi_fulltext.py` is the corrected rerun, `rep5d_vs_paper_points.py` compares it with the paper's own simulation points; `rep5_ghanassi.py` kept as the earlier version; R7: `rep7_bergmans.py`, log in `replication/results/rep7_log.txt`) | `replication/results/` |
| 4 (R2) MATLAB cross-check (run by the team in MATLAB R2025b) | `export_for_matlab.py`, `matlab/mathworks_crosscheck.m` | `matlab/matlab_output_R2025b.txt` |
| 5.1 P1 validation, misadjustment correction, delay | `p1_validation.py`, `investigate_misadjustment.py`, `misadj_lib.py`, `c2_delay_nmp.py` | `results/p1_*`, `results/misadjustment_*`, `results/commit/c2*` |
| 5.2 P2 abrupt transitions | `p2_final_NT120k.py` (`p2_final.py` = earlier N_T = 60000 run) | `results/p2_final_NT120k_*` |
| 5.3-5.4 P3-P4 boundary, optimum step | `final_sweep.py`, `final_analyse.py`, `final_tables.py`, `sweep_analyse.py` | `results/final/` |
| 5.5 coefficient trajectories | `c6_traj.py`, `c6b_traj_series.py` (saves the curves; identical numbers) | `results/commit/c6*` |
| 5.6 triangle vs sinusoid | `c1_tri_sin.py` | `results/commit/c1*` |
| 5.7 decision-directed / pilot | `dd_lib.py`, `c5_dd.py`, `c5b_dd_stress.py`, `c5c_dd_mu.py` | `results/commit/c5*` |
| 6.1-6.2 audio and image payloads | `audio_demo.py`, `audit/p5_independent_check.py`, `c10_image.py`, `c10b_image_lowsnr.py`, `c10c_image_fig.py` | `results/p5/`, `results/commit/c10*` |
| 6.3 P6 word length (L2) | `fxp_lib.py`, `p6a_tests.py`, `p6b_tests.py`, `p6c_surface.py` (`run_p6c.sh`), `p6c_tables.py`, `p6c_fig.py` | `results/p6a/`, `results/p6c/` |
| 6.4 first RTL (L3) | `rtl/*.v`, `rtl/run_rx_tests.py`, `rtl/run_chain_tests.py`, `rtl/gen_noise_vectors.py` | `rtl/*_log.txt` |
| 7 theory model | `model_boundary.py`, `model_explain.py` | `results/model/` |
| all report figures | `report_figs.py` (style: `report_style.py`) - redraws every figure from the saved result files; no experiment is rerun | `results/report_figs/` |

Core library: `config.py` (all parameters), `lms_lib.py` (channel, noise, the LMS loop for R2/R3, oracle), `exp_lib.py`.
The LMS loop (`lms_lib.lms_receivers`) is the same in every experiment: y = w·u before the update, w ← w + μ·e·u.
Seeds: pilot 1000–1099 (parameter choice only), final 2000–2099; other seed ranges are stated in each script.
AI use: the code was written with the AI assistant Claude under the team's direction (Sec. 9 of the report).

| BER against MSE (Sec. 5.3, Fig. bermse) | `report_figs.py bermse` (existing L1 analysis files only, no new runs) | `results/report_figs/bermse.pdf` |
