# Mid-term findings re-measured on the Boolean Board (L5) vs the mid-term simulation (L1)

Board: supervised LMS, LFSR sum-of-uniforms noise, fixed point of the loaded build. L1: float, Gaussian noise. Same grid, rules and analysis code (sweep_analyse.analyse, unchanged); L1 restricted to the same 7 step sizes and seeds.

## primary channel, 16 dB, build m12_a26_r1, 100 seeds

| mu | S*_MSE board | S*_MSE L1 (7 mu) | S*_MSE L1 published | S*_BER board | S*_BER L1 | S_cross board | S_cross L1 | static eps board / L1 |
|---|---|---|---|---|---|---|---|---|
| 2^-5 | 14 | 14 | 14 | 5 (resolved) | 5 (resolved) | 2 | 2 | 1.208 / 1.199 |
| 2^-6 | 10 | 10 | 10 | bracket (28, 14) | 20 (conditional) | none | none | 0.388 / 0.389 |
| 2^-7 | 20 | 20 | 20 | bracket None | bracket None | none | none | 0.166 / 0.167 |
| 2^-8 | 28 | 28 | 28 | bracket (80, 20) | bracket (56, 28) | none | none | 0.077 / 0.078 |
| 2^-9 | 56 | 56 | 56 | bracket (112, 56) | bracket None | none | none | 0.037 / 0.038 |
| 2^-10 | 112 | 112 | 112 | bracket (224, 80) | bracket None | none | none | 0.018 / 0.019 |
| 2^-11 | 224 | 224 | 224 | bracket (500, 160) | bracket (500, 160) | none | none | 0.014 / 0.015 |

mu_opt exponent (baseline variant): board 0.4756299396436295 (14 pts), L1 7-mu 0.47631501803908893 (14 pts), L1 published 14-mu 0.5189956303460698; board spread (0.43665440305736575, 0.5381144169509288), L1 7-mu spread (0.4374005313474302, 0.5381144169509288)

R3 MSE board vs L1, relative difference over all (S, mu): median -0.05 %, range -0.32 .. +0.40 %

Stall fraction at S = 28 (board): 2^-5: 0.00 %, 2^-6: 0.00 %, 2^-7: 0.00 %, 2^-8: 0.00 %, 2^-9: 0.01 %, 2^-10: 0.02 %, 2^-11: 0.05 %
