### Table 1 — S*_MSE (ρ_th = 0.5; bands ρ_th 0.25 / 0.75; literal-baseline sensitivity)

| μ | primary 16 dB | primary 14 dB | primary 12 dB | control 16 dB | control 14 dB |
|---|---|---|---|---|---|
| 2^-5 | **14** (20/10; lit None) | ρ undefined* | ρ undefined* | **10** (14/10; lit 14) | **56** (80/40; lit None) |
| 2^-5.5 | **10** (20/10; lit 14) | **14** (20/10; lit 28) | **28** (40/28; lit None) | **10** (14/10; lit 10) | **10** (20/10; lit 20) |
| 2^-6 | **10** (20/10; lit 14) | **14** (20/10; lit 14) | **14** (28/10; lit 28) | **10** (14/10; lit 10) | **10** (20/10; lit 14) |
| 2^-6.5 | **14** (28/10; lit 14) | **14** (28/10; lit 14) | **14** (28/10; lit 20) | **14** (20/10; lit 14) | **14** (20/10; lit 14) |
| 2^-7 | **20** (28/10; lit 20) | **20** (28/10; lit 20) | **20** (28/10; lit 20) | **14** (28/10; lit 14) | **20** (28/10; lit 20) |
| 2^-7.5 | **20** (40/10; lit 20) | **20** (40/10; lit 20) | **20** (40/14; lit 28) | **20** (40/14; lit 20) | **20** (40/14; lit 20) |
| 2^-8 | **28** (56/14; lit 28) | **28** (56/14; lit 28) | **28** (56/14; lit 28) | **28** (56/14; lit 28) | **28** (56/20; lit 28) |
| 2^-8.5 | **40** (80/20; lit 40) | **40** (80/20; lit 40) | **40** (80/20; lit 40) | **40** (80/20; lit 40) | **40** (80/20; lit 40) |
| 2^-9 | **56** (112/28; lit 56) | **56** (112/28; lit 56) | **56** (112/28; lit 56) | **56** (112/28; lit 56) | **56** (112/28; lit 56) |
| 2^-9.5 | **80** (160/40; lit 80) | **80** (160/40; lit 80) | **80** (160/40; lit 80) | **80** (160/40; lit 80) | **80** (160/40; lit 80) |
| 2^-10 | **112** (224/56; lit 112) | **112** (224/40; lit 112) | **112** (224/40; lit 112) | **112** (224/56; lit 112) | **112** (224/56; lit 112) |
| 2^-10.5 | **160** (320/80; lit 160) | **160** (320/56; lit 160) | **160** (320/56; lit 160) | **160** (320/80; lit 160) | **160** (320/80; lit 160) |
| 2^-11 | **224** (500/112; lit 224) | **224** (500/80; lit 224) | **160** (500/80; lit 160) | **224** (500/112; lit 224) | **224** (500/112; lit 224) |
| 2^-11.5 | **320** (1000/160; lit 320) | **320** (500/112; lit 320) | **224** (500/112; lit 320) | **320** (500/160; lit 320) | **320** (500/160; lit 320) |

*ρ undefined: the static LMS excess already exceeds the plateau (ε_static ≥ ε_plateau), so the tracking-loss scale has no room.

### Table 2 — S*_BER (f = 2; primary method = paired seed bootstrap; R = resolved, C = conditional; [a, b] = transition bracket when the boundary point itself is inconclusive, S*_BER not demonstrated under the strict rule)

| μ | 12 dB (100 seeds) | 14 dB (100 seeds, or 1500 seeds for μ ≤ 2^-7) | 16 dB (100 seeds) | f = 1.5 / 5 at 12 dB |
|---|---|---|---|---|
| 2^-5 | **2** (R) | **5** (R) | **5** (R) | 5 / None |
| 2^-5.5 | **5** (R) | **10** (R) | **10** (R) | 10 / None |
| 2^-6 | **10** (R) | **14** (R) | **20** (C) | 14 / 5 |
| 2^-6.5 | **14** (R) | n.d. [28, 14] | n.d. [80, 14] (C) | None / 5 |
| 2^-7 | n.d. [28, 14] | **40** (R) | n.d. (reference-limited) | 40 / 10 |
| 2^-7.5 | **40** (R) | **80** (R) | n.d. (reference-limited) | None / 14 |
| 2^-8 | **56** (R) | **112** (R) | n.d. [56, 28] (C) | 80 / 20 |
| 2^-8.5 | **80** (R) | **160** (R) | n.d. (reference-limited) | None / None |
| 2^-9 | **112** (R) | n.d. [320, 160] | n.d. (reference-limited) | None / None |
| 2^-9.5 | n.d. [224, 112] | n.d. [500, 224] | n.d. [320, 56] (C) | None / None |
| 2^-10 | n.d. [320, 160] | n.d. [1000, 320] | n.d. (reference-limited) | None / None |
| 2^-10.5 | n.d. [500, 224] | **1000** (R) | n.d. [320, 160] (C) | None / 160 |
| 2^-11 | **500** (R) | n.d. [2000, 500] | n.d. [500, 160] (C) | 1000 / 224 |
| 2^-11.5 | n.d. [1000, 320] | n.d. [2000, 500] | n.d. [500, 224] (C) | 1000 / 320 |

### Table 3 — BER status strings (S from 5000 on the left to 1 on the right; P/F/? = resolved pass/fail/inconclusive, p = conditional pass)

| μ | 12 dB | 14 dB | 16 dB | control 14 dB |
|---|---|---|---|---|
| 2^-5 | `PPPPPPPPPPPPPPPPPF` | `PPPPPPPPPPPPPPPPFF` | `PPPPPPPPPPPPPPPPFF` | `ppppppppppppppppFF` |
| 2^-5.5 | `PPPPPPPPPPPPPPPPFF` | `PPPPPPPPPPPPPPPFFF` | `PPPPPPPPPPPPPPPFFF` | `pp??p?p??p??????FF` |
| 2^-6 | `PPPPPPPPPPPPPPPFFF` | `PPPPPPPPPPPPPPFFFF` | `pppppppppppppFFFFF` | `pp?ppppppp??ppp?FF` |
| 2^-6.5 | `PPPPPPPPPPPPPPFFFF` | `PPPPPPPPPPPP?FFFFF` | `ppppppppp????FFFFF` | `ppppppppppppppp???` |
| 2^-7 | `PPPPPPPPPPPP?FFFFF` | `PPPPPPPPPPPFFFFFFF` | `ppppp?ppp???FFFFFF` | `ppppppppppppppp???` |
| 2^-7.5 | `PPPPPPPPPPPFFFFFFF` | `PPPPPPPPPFFFFFFFFF` | `ppppp?ppp???FFFFFF` | `ppppppppppppppp?p?` |
| 2^-8 | `PPPPPPPPPPFFFFFFFF` | `PPPPPPPPFFFFFFFFFF` | `pppppppppp?FFFFFFF` | `ppppppppppppppppp?` |
| 2^-8.5 | `PPPPPPPPPFFFFFFFFF` | `PPPPPPPFFFFFFFFFFF` | `pppppp?p??FFFFFFFF` | `ppppppppppppppppp?` |
| 2^-9 | `PPPPPPPPFFFFFFFFFF` | `PPPPP?FFFFFFFFFFFF` | `ppppp??p??FFFFFFFF` | `ppppppppppppppppp?` |
| 2^-9.5 | `PPPPPP?FFFFFFFFFFF` | `PPPP?FFFFFFFFFFFFF` | `ppppp????FFFFFFFFF` | `ppppppppppppppppp?` |
| 2^-10 | `PPPPP?FFFFFFFFFFFF` | `PPP?FFFFFFFFFFFFFF` | `ppppp??F?FFFFFFFFF` | `ppppppppppppppppp?` |
| 2^-10.5 | `PPPP?FFFFFFFFFFFFF` | `PPPFFFFFFFFFFFFFFF` | `ppppp?FFFFFFFFFFFF` | `ppppppppppppppppp?` |
| 2^-11 | `PPPPFFFFFFFFFFFFFF` | `PP?FFFFFFFFFFFFFFF` | `pppp??FFFFFFFFFFFF` | `ppppppppppppppppp?` |
| 2^-11.5 | `PPP?FFFFFFFFFFFFFF` | `PP?FFFFFFFFFFFFFFF` | `pppp?FFFFFFFFFFFFF` | `ppppppppppp?ppppp?` |

### Table 4 — S_cross (paired bootstrap of BER_R3 − min(BER_R1, BER_R2) per S; A = R3 advantage demonstrated, L = loss of advantage confirmed, ? = inconclusive: advantage not demonstrated and no loss confirmed)

Three different statements must not be confused: (i) **'A at every S'** = R3 advantage demonstrated at every grid point; (ii) **'no crossover confirmed'** = no point is L, but some points may be '?' (advantage not demonstrated there); (iii) **'crossover (L) confirmed'**.

| run | μ in the run (count; seeds) | μ with A at every S | μ with a confirmed loss (L) | μ with only '?' (no L) | detail for μ without A at every S |
|---|---|---|---|---|---|
| primary_16 | 2^-5 … 2^-11.5 (14; 100 seeds) | 12 of 14 | 1 | 1 | 2^-5: status string (S = 5000 … 1) `AAAAAAAAAAAAAAAALL`; 2^-5.5: status string (S = 5000 … 1) `AAAAAAAAAAAAAAAAA?` |
| primary_14 | 2^-5 … 2^-11.5 (14; 100 seeds) | 13 of 14 | 1 | 0 | 2^-5: status string (S = 5000 … 1) `AAAAAAAAAAAAAAAALL` |
| primary_12 | 2^-5 … 2^-11.5 (14; 100 seeds) | 13 of 14 | 1 | 0 | 2^-5: status string (S = 5000 … 1) `AAAAAAAAAAAAAAAALL` |
| primary_14_ber14 | 2^-7 … 2^-11.5 (10; 1500 seeds) | 10 of 10 | 0 | 0 | — |
| control_16 | 2^-5 … 2^-11.5 (14; 100 seeds) | 0 of 14 | 1 | 13 | 2^-5: status string (S = 5000 … 1) `AAAAAAAAAA?AAAAA?L`; 2^-5.5: status string (S = 5000 … 1) `AA?AAAAAAAAAA??A??`; 2^-6: status string (S = 5000 … 1) `AA???A?????A?????A`; 2^-6.5: status string (S = 5000 … 1) `A??A?A???????????A`; … (13 μ with only '?') |
| control_14 | 2^-5 … 2^-11.5 (14; 100 seeds) | 13 of 14 | 1 | 0 | 2^-5: status string (S = 5000 … 1) `AAAAAAAAAAAAAAAAAL` |

### Table 5 — optimum step size exponent d log2 μ_opt / d log2(1/S)

| run | baseline fit | systematic band (7 variants) | statistical 95 % (seed bootstrap) | points |
|---|---|---|---|---|
| primary_16 | 0.519 | 0.487 – 0.543 | 0.5187 – 0.5193 | 15 |
| primary_14 | 0.525 | 0.493 – 0.550 | 0.5250 – 0.5257 | 15 |
| primary_12 | 0.511 | 0.476 – 0.542 | 0.5103 – 0.5110 | 14 |
| control_16 | 0.593 | 0.570 – 0.610 | 0.5932 – 0.5937 | 15 |
| control_14 | 0.575 | 0.551 – 0.596 | 0.5744 – 0.5749 | 14 |