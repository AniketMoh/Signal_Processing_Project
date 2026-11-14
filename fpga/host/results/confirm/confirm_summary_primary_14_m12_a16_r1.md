# Mid-term findings re-measured on the Boolean Board (L5) vs the mid-term simulation (L1)

Board: supervised LMS, LFSR sum-of-uniforms noise, fixed point of the loaded build. L1: float, Gaussian noise. Same grid, rules and analysis code (sweep_analyse.analyse, unchanged); L1 restricted to the same 7 step sizes and seeds.

## primary channel, 14 dB, build m12_a16_r1, 100 seeds

| mu | S*_MSE board | S*_MSE L1 (7 mu) | S*_MSE L1 published | S*_BER board | S*_BER L1 | S_cross board | S_cross L1 | static eps board / L1 |
|---|---|---|---|---|---|---|---|---|
| 2^-5 | None | None | None | 5 (resolved) | 5 (resolved) | 2 | 2 | 1.185 / 1.178 |
| 2^-6 | 14 | 14 | 14 | bracket (20, 10) | 14 (resolved) | none | none | 0.384 / 0.384 |
| 2^-7 | 20 | 20 | 20 | bracket (56, 28) | bracket (80, 28) | none | none | 0.164 / 0.165 |
| 2^-8 | 28 | 28 | 28 | bracket None | bracket (224, 56) | none | none | 0.076 / 0.077 |
| 2^-9 | 56 | 56 | 56 | bracket (500, 112) | bracket (320, 112) | none | none | 0.037 / 0.038 |
| 2^-10 | 112 | 112 | 112 | bracket (1000, 224) | bracket None | none | none | 0.018 / 0.019 |
| 2^-11 | 224 | 224 | 224 | bracket (2000, 500) | bracket (2000, 320) | none | none | 0.012 / 0.012 |

mu_opt exponent (baseline variant): board 0.4888975697544135 (14 pts), L1 7-mu 0.49268977761410293 (14 pts), L1 published 14-mu 0.5253316365694138; board spread (0.4560019564337969, 0.5426521677585436), L1 7-mu spread (0.4570310538186616, 0.5426521677585436)

R3 MSE board vs L1, relative difference over all (S, mu): median -0.07 %, range -0.30 .. +0.32 %

Stall fraction at S = 28 (board): 2^-5: 0.97 %, 2^-6: 2.11 %, 2^-7: 4.01 %, 2^-8: 7.05 %, 2^-9: 12.12 %, 2^-10: 20.73 %, 2^-11: 34.25 %
