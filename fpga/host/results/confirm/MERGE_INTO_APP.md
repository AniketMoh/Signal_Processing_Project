# Moving the board-confirmation section into the application copy of the report

The board re-measurement (§7.5 "The mid-term findings re-measured on the board") was written in the **original** folder (`Signal_Processing_Project`, branch `fpga-implementation`). The application copy (`Signal_Processing_Project_app`, branch `application`) was created before that, so its report does not have it yet. I did not edit the application copy, because another chat was working in it. Nothing is committed in either folder.

## 1. §7.5, table and figure: one command (checked, applies cleanly)

From `C:\Users\Pradeep\Signal_Processing_Project_app`:

```
git apply ..\Signal_Processing_Project\fpga\host\results\confirm\final_report_s_fpga_confirm.patch
copy ..\Signal_Processing_Project\final_report\figs\confirm.pdf final_report\figs\confirm.pdf
```

## 2. Abstract and conclusion: paste by hand

The application chat rewrote these paragraphs, so the patch does not apply to them. Paste one sentence in each.

**`final_report/s0_abstract_intro.tex`**, in the abstract, after the sentence ending "…meets 100\,MHz without delayed LMS (\lvl{L4})." (or wherever the board results are summarised):

```
Re-run on the board with the mid-term's grid and seeds ($1.2\times10^5$ runs), the tracking boundary is reproduced in every case, and so are the step-size optimum and the 1.47-fold misadjustment; below a BER of about $10^{-4}$ the board errs less, exactly as its bounded noise generator predicts.
```

In the contributions list, the P7–P10 item can end with:

```
and a re-measurement of the mid-term's boundary sweep on the hardware (\cref{sec:fpga,sec:confirm,fig:teaser});
```

**`final_report/s7_conclusion.tex`**, at the end of item "The hardware equals the model", before its closing `}`:

```
 Re-run on the board with the mid-term's grid, rules and 100 seeds, the boundary sweep reproduces every $S^\star_{\rm MSE}$ (35 of 35 cases, and all seven of the 26-bit build), the step-size optimum and the 1.47-fold misadjustment; the only difference, a lower BER below about $10^{-4}$, is predicted exactly by the bounded sum-of-uniforms hardware noise (\cref{sec:confirm}).
```

## 3. Rebuild and check

```
cd final_report
pdflatex main.tex & bibtex main & pdflatex main.tex & pdflatex main.tex
```

Check that the log has no `undefined` references and that §7.5 (table "Tracking boundaries measured on the board", figure with panels a–d) appears after the image/voice paragraph of §7.4. In the original folder this compiled to 29 pages with no errors, warnings or overfull lines (before the application section was added).

## Data and scripts the section relies on

Everything is under `fpga/host/confirm/` (scripts) and `fpga/host/results/confirm/` (data, tables, figures, `CONFIRMATION_REPORT.md`). The application copy already has an older copy of `fpga/host/confirm/`, taken before the checkpointing fix. Copy the folder over if the scripts should travel with that branch.
