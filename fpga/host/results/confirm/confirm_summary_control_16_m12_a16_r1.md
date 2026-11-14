# Mid-term findings re-measured on the Boolean Board (L5) vs the mid-term simulation (L1)

Board: supervised LMS, LFSR sum-of-uniforms noise, fixed point of the loaded build. L1: float, Gaussian noise. Same grid, rules and analysis code (sweep_analyse.analyse, unchanged); L1 restricted to the same 7 step sizes and seeds.

## control channel, 16 dB, build m12_a16_r1, 100 seeds

| mu | S*_MSE board | S*_MSE L1 (7 mu) | S*_MSE L1 published | S*_BER board | S*_BER L1 | S_cross board | S_cross L1 | static eps board / L1 |
|---|---|---|---|---|---|---|---|---|
| 2^-5 | 10 | 10 | 10 | bracket None | bracket None | 1000 | 40 | 0.598 / 0.596 |
| 2^-6 | 10 | 10 | 10 | bracket None | bracket None | 2000 | 1000 | 0.236 / 0.236 |
| 2^-7 | 14 | 14 | 14 | bracket None | bracket None | 5000 | 2000 | 0.107 / 0.107 |
| 2^-8 | 28 | 28 | 28 | bracket None | bracket None | 5000 | 2000 | 0.051 / 0.052 |
| 2^-9 | 56 | 56 | 56 | bracket None | bracket None | 5000 | 5000 | 0.025 / 0.026 |
| 2^-10 | 112 | 112 | 112 | bracket None | bracket None | 5000 | 5000 | 0.013 / 0.013 |
| 2^-11 | 224 | 224 | 224 | bracket None | bracket None | 5000 | 2000 | 0.007 / 0.007 |

mu_opt exponent (baseline variant): board 0.55689502798844 (14 pts), L1 7-mu 0.5612168885737188 (14 pts), L1 published 14-mu 0.5934318603319976; board spread (0.5301465421674991, 0.583857914699905), L1 7-mu spread (0.531128709184436, 0.5891549174350647)

R3 MSE board vs L1, relative difference over all (S, mu): median -0.01 %, range -0.18 .. +0.18 %

Stall fraction at S = 28 (board): 2^-5: 0.60 %, 2^-6: 1.40 %, 2^-7: 2.87 %, 2^-8: 5.48 %, 2^-9: 10.26 %, 2^-10: 19.27 %, 2^-11: 35.45 %
