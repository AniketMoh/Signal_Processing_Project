# PPR-22 versus current project state — classification (revised 20 Oct 2026, owner decision E-7)

Sources: PPR-22, `DECISIONS.md`, `AUDIT_REPORT.md` (section C holds the full section-by-section compliance matrix with quotations and evidence). All numbers are L1 pilot results.

**Why this revision.** The earlier version listed 9 "contradictions". Under the stricter definitions requested in the audit, most of them are justified methodological changes or findings. Only four statements of PPR-22 genuinely conflict with what the project does or knows. **None of the four is an experimental contradiction:** no measured result contradicts a PPR-22 measurement plan or hypothesis.

## 1. The four labelled issues

| # | Label | PPR-22 statement | What is true now | Type | Handling in the midterm report |
|---|---|---|---|---|---|
| I-1 | **AI-disclosure conflict** | Sec. 15: "No simulation output … in this or any subsequent report is AI-generated; all such results are produced and verified independently." | Code and simulations were developed with AI assistance. The course flier only requires disclosure of where AI was used. | Reporting/policy wording, not experimental. Owner priority: low. | Replace with the revised disclosure (D-06): state where AI was used. |
| I-2 | **Incorrect R approximation** | Sec. 5.4: an LFSR training sequence gives R ≈ σ²I | R = H Hᵀ + σ²I. The PRBS whitens the transmitted symbols, not the equalizer input, which is filtered by the channel. | Theoretical statement in PPR-22; no experiment depended on it. | One-sentence correction (register R-6). |
| I-3 | **Bounded-channel mismatch overstatement** | Sec. 6.2: after update underflow "the mismatch grows without bound and R3 degenerates into R2" | The trajectory is bounded, so the mismatch is bounded too. Whether updates stall, drift or are biased depends on rounding and accumulator width. | Theoretical statement in PPR-22; it will be tested in P6. | Corrected wording (register R-7). |
| I-4 | **Midterm schedule deviation** | Sec. 9: "P1–P6 are software and constitute the mid-term target" | P5 (recorded audio) and P6 (fixed-point model) are not yet done. A plan now targets both before 25 Oct (`FREEZE_1_CHECKLIST.md` §6). | Planning. | Report what is delivered. If P6 is only partly delivered (scope P6a), state the remaining P6 items as deferred. |

## 2. Justified methodological changes (recorded with reasons; the original version is also reported where it can be computed)

| Item | PPR-22 | Now | Reason |
|---|---|---|---|
| Channel range | Sec. 4.2 a in [0.20, 0.60], marked "provisionally" | Mild channel kept as the **control** (in the final sweep, E-4); harsher **primary** channel a in [0.3125, 0.906] | The mild channel's eye never closes; selection rule C1–C4 |
| Recovery time N_rec | Sec. 4.1: return within a factor of the *pre*-transition level | *Post*-transition level, sustained (D-09) | Channels A and B have different attainable MSE; the literal version is reported where it is defined |
| "Static-channel value" in S*_BER | Sec. 5.7 (channel value not specified) | Trajectory-averaged measured static baseline; the literal c_lo version is a sensitivity column | Misadjustment depends on the channel state |
| BER operating points | Sec. 10: one fixed SNR plus a sensitivity sweep | 16 dB primary (MSE/tracking), 14 dB secondary; BER resolved at 12/14 dB | At 16 dB the static BER is too small to measure for small μ |
| BER statistics | not specified | Paired seed-level bootstrap (primary, E-1); burst-adjusted and plain Wilson as sensitivities; reference-limited labels | Errors come in bursts; the reference has its own uncertainty |
| Optimum step-size exponent | Sec. 5.2: "specifically … square root" | Square root tested; 2/3 ramp exponent as a conditional alternative; measured exponent with statistical and systematic uncertainty | The trajectories are deterministic ramps |
| S presets | Table 2 S1–S4, "provisional … fixed after simulation" | 18-value grid that brackets the boundary | Fulfils PPR-22's own instruction |
| P2 training length | not specified | N_T = 60000 for P2 (validated), 30000 for the continuous sweep (validated) | The "down" step trains on the harsh channel |

## 3. Findings and extensions (add to PPR-22, do not conflict with it)
- **F-1 (finding):** the textbook misadjustment (Sec. 5.2, "roughly μ tr(R)/2") underestimates by 1.47× on this channel. PPR-22 itself says "exact constants depend on the model".
- **Oracle-normalised ε, ρ and S*_MSE.**
- **Validation suite V0–V7 plus V2c** (Gaussian tail validated to 2.7·10⁻⁷).
- **Correlated-error misadjustment model and mean-weight predictions.**
- **B_mul / B_acc split.**
- **Seed discipline and FREEZE-1 gate.**
- **Labelling note (not a contradiction, D-12):** the 10⁻⁴ BER reporting limit of Sec. 4.3 belongs to the hardware noise generator. L1 uses ideal Gaussian noise and is labelled, with a dashed 10⁻⁴ line on BER figures.
- **The UART symbol rate** (Sec. 6.3, 10⁴ symbols/s) is a design target below the 92 ksym/s ceiling: no conflict (previously listed by mistake).

## 4. Open commitments of PPR-22 (not contradictions unless dropped silently)

| Commitment | Status |
|---|---|
| Sec. 4.2 triangle vs sinusoid comparison in floating point | Not started |
| Sec. 5.3 a non-minimum-phase preset (h = [0.5, 1.0]) to show why the Δ sweep is needed | Not started |
| Sec. 5.6 decision-directed mode (and pilot-assisted) | Code path exists, untested |
| Sec. 5.7 coefficient trajectories vs the channel trajectory (continuous variation) | P2 done; continuous pending |
| Sec. 4.3 LFSR noise generator and its validation | Planned in P6a |
| Sec. 7.2 recorded-audio demonstration (P5) | Planned before 25 Oct |
| Sec. 6.1–6.4 fixed-point model, saturation, precision sweep (P6) | P6a planned before 25 Oct, the rest in the final phase |
| Sec. 12.6 MathWorks cross-check | Not started |
| Sec. 14 prior 128 × 72 image result | Configuration undocumented; label or reproduce |
| Sec. 6.5 parallel datapath, Sec. 13 board demonstration | Final phase (D-05: parallel kept) |

## 5. Register rows (added to `DECISIONS.md`)
- R-12: I-1 disclosure wording.
- R-13: F-1 qualification of Eq. (9).
- R-14: I-4 midterm scope.
- R-15: L1 Gaussian noise / 10⁻⁴ hardware limit.
- R-16: S grid replaces Table 2.
- R-17: SNR operating points.
- R-18: trajectory-averaged static baseline.
- R-19: BER statistics (paired bootstrap).
- R-20: P2 training length 60000.
- R-6 and R-7 keep the I-2 and I-3 corrections. R-9 stays "no change" (parallel datapath).
