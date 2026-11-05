mtr-22 — EE2000 mid-term report, team 22
=========================================

mtr-22.pdf                         the mid-term report (23 pages)
1_report_source/                   LaTeX source (main.tex) and the report figures (figs/)
2_code_and_results_by_phase/       all code, results, figures and audio, grouped by phase

Inside 2_code_and_results_by_phase/ every phase folder has the same sub-folders:
  code/            scripts for that phase
  report_figures/  the figures of the report that belong to that phase (FigNN = figure number in the PDF)
  figures/         working plots made during the experiments
  results/         data, logs and analysis files (JSON, NPZ, TXT)
  audio/           sound files (P5 only)

Folder                                          Report section            Report figures
00_shared_library                               (used by all)             -  (also report_figs.py, which draws every figure)
01_method_pilot_and_statistics_checks           Sec. 2  method            -  (pilot runs, grids, bootstrap and noise checks)
02_replications_R1-R7                           Sec. 4  replications      Fig. 2, 3  (MATLAB cross-check in matlab/)
03_P1_validation                                Sec. 5.1 P1               Fig. 4, 5
04_P2_abrupt_transitions                        Sec. 5.2 P2               Fig. 6, 7
05_P3-P4_boundary_and_optimum_step              Sec. 5.3-5.4 P3-P4        Fig. 8-12
06_trajectories_sinusoid_decision-directed      Sec. 5.5-5.7              Fig. 13-15
07_P5_audio_and_image                           Sec. 6.1-6.2 P5           Fig. 16-18
08_P6_fixed_point                               Sec. 6.3 P6 (L2)          Fig. 19
09_P7-P8_RTL                                    Sec. 6.4 RTL (L3)         -
10_theory_model                                 Sec. 7  theory            Fig. 20
(Fig. 1, the block diagram, is drawn in the LaTeX source.)

Running the code
  The scripts import each other and read "results/..." paths, so they run from the original
  flat layout, not from the phase folders. To get it:
      cd 2_code_and_results_by_phase
      python3 make_runnable_copy.py        (creates runnable_code/ with every file in place)
      cd runnable_code && python3 report_figs.py     (redraws all report figures)
  manifest.csv lists, for every file, its phase-folder location and its runnable path.
  00_shared_library/code/README.md maps each report section to its scripts.
