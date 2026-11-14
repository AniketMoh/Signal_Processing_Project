# Mid-term findings re-measured on the Boolean Board (L5) vs the mid-term simulation (L1)

Board: supervised LMS, LFSR sum-of-uniforms noise, fixed point of the loaded build. L1: float, Gaussian noise. Same grid, rules and analysis code (sweep_analyse.analyse, unchanged); L1 restricted to the same 7 step sizes and seeds.

## control channel, 14 dB, build m12_a16_r1, 100 seeds

| mu | S*_MSE board | S*_MSE L1 (7 mu) | S*_MSE L1 published | S*_BER board | S*_BER L1 | S_cross board | S_cross L1 | static eps board / L1 |
|---|---|---|---|---|---|---|---|---|
| 2^-5 | 56 | 56 | 56 | bracket (10, 2) | 5 (conditional) | 2 | 1 | 0.599 / 0.598 |
| 2^-6 | 10 | 10 | 10 | bracket None | bracket None | none | none | 0.236 / 0.236 |
| 2^-7 | 20 | 20 | 20 | bracket None | bracket None | none | none | 0.107 / 0.107 |
| 2^-8 | 28 | 28 | 28 | bracket None | bracket None | none | none | 0.051 / 0.052 |
| 2^-9 | 56 | 56 | 56 | bracket None | bracket None | none | none | 0.025 / 0.026 |
| 2^-10 | 112 | 112 | 112 | bracket None | bracket None | none | none | 0.013 / 0.013 |
| 2^-11 | 224 | 224 | 224 | bracket None | bracket None | none | none | 0.007 / 0.007 |

mu_opt exponent (baseline variant): board 0.5383442035018462 (13 pts), L1 7-mu 0.5399787363702788 (13 pts), L1 published 14-mu 0.5746509401463072; board spread (0.5121064979554681, 0.5863286649193695), L1 7-mu spread (0.5129221262279358, 0.5863286649193695)

R3 MSE board vs L1, relative difference over all (S, mu): median -0.04 %, range -0.16 .. +0.10 %

Stall fraction at S = 28 (board): 2^-5: 0.51 %, 2^-6: 1.18 %, 2^-7: 2.45 %, 2^-8: 4.76 %, 2^-9: 9.03 %, 2^-10: 17.11 %, 2^-11: 31.75 %
