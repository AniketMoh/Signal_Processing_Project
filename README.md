# Signal Processing Project

**FPGA-Based LMS Tracking of Time-Varying ISI Channels: How Fast Can a Channel Change Before a Fixed-Point Equalizer Loses It?**

EE2000 (Signal Processing) course project, IIT Hyderabad. Mid-term report due 25 Oct 2026.

This repository holds the project documentation exported from the Claude project of the same name on 20 Oct 2026. The simulation code and result files that these documents refer to (`code/…`) are not part of this export.

## Layout

| Path | Contents |
|---|---|
| `reference/PPR-22.pdf` | Preliminary report (the original proposal) |
| `reference/project.pdf` | Project description with deadlines |
| `docs/PROJECT_PROMPT.md` | Master project prompt (the shared specification) |
| `docs/PROJECT_SPEC.md` | Project specification v1.2 |
| `docs/DECISIONS.md` | Decision log, findings F-1 … F-7 and the PPR-22 change register |
| `docs/AUDIT_REPORT.md` | Audit of PPR-22 against the implementation |
| `docs/PPR22_COMPARISON.md` | Classification of differences from PPR-22 |
| `docs/PROPOSALS_P10_P11_P12.md` | Wording of the BER criteria, V2 test and static baseline |
| `docs/FREEZE_1_PROPOSED.md`, `docs/FREEZE_1_CHECKLIST.md` | FREEZE-1 configuration and approval checklist |
| `docs/STAGE_P1_NOTES.md`, `docs/STAGE_P2_P3_NOTES.md` | Plain-language stage notes (P1, P2, P3) |
| `docs/MISADJUSTMENT_DERIVATION.md` | Derivation behind finding F-1 |
| `docs/RESULTS_FINAL_L1.md` | Final L1 results (tracking sweep, abrupt transitions) |
| `docs/P6A_REPORT.md` | Fixed-point (L2) model results |

## Validation levels

L1 floating-point simulation · L2 fixed-point simulation · L3 RTL simulation · L4 Vivado synthesis · L5 board measurement. No result in these documents is an L3–L5 result.
