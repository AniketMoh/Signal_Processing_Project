# figs — plots of the EE2000 FPGA-LMS tracking project

All plots are simulation results: level L1 (floating point, ideal Gaussian noise) unless the name says L2 (`fig_P6a_*`, bit-true fixed point). No plot here is a hardware result. LMS is supervised (known transmitted bits as reference) in every experiment.

## Final L1 abrupt-transition results (P2), N_T = 120000
`P2_final_L1_NT120000_<16|14>dB_<ber_vs_time|coefficients|mse_vs_time|nrec_vs_mu>.png`
- 100 final seeds (2000-2099), training length N_T = 120000 symbols, steps large_up / mid_up / down, μ = 2^-7 … 2^-10.
- These replace the N_T = 60000 run (change R-21 in `DECISIONS.md`). A label strip at the top of each image states the configuration.

## Archived results (superseded, kept unchanged)
`archive_P2_NT60000/` — the same P2 experiment with N_T = 60000 (byte-identical to the original plots). Superseded because 60000 symbols left a small residual weight error in the slowest mode (finding F-7).

## Other plots
- `fig_P2_*.png` — P2 L1 **pilot** (pilot seeds, earlier setup), not final.
- `fig_P1_*`, `fig_V*`, `fig_M1_*` — validation of the LMS library and misadjustment investigation.
- `fig_P3_*` — P3 continuous-variation **pilot**.
- `fig_ber_vs_S_*`, `fig_rho_vs_S_*`, `fig_eps_heatmap_*`, `fig_mu_opt_*`, `fig_boundaries_vs_mu.png` — final L1 sweep (N_T = 30000, 100 final seeds).
- `fig_P6a_T4_coefficients.png` — L2 fixed-point model.
- `fig_P5_audio_L1_supervised.png` — P5 recorded-audio demonstration (owner's voice, L1, supervised LMS, one noise realization).
- `fig_audit_execution_flow.png`, `fig_explain_S_and_mu.png` — diagrams.
