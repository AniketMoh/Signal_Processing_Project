# Mid-term findings re-measured on the Boolean Board (L5) vs the mid-term simulation (L1)

Board: supervised LMS, LFSR sum-of-uniforms noise, fixed point of the loaded build. L1: float, Gaussian noise. Same grid, rules and analysis code (sweep_analyse.analyse, unchanged); L1 restricted to the same 7 step sizes and seeds.

## primary channel, 12 dB, build m12_a16_r1, 100 seeds

| mu | S*_MSE board | S*_MSE L1 (same mu) | S*_MSE L1 published | S*_BER board | S*_BER L1 | S*_BER L1 published | S_cross board | S_cross L1 | static eps board / L1 |
|---|---|---|---|---|---|---|---|---|---|
| 2^-5 | None | None | None | 2 (resolved) | 2 (resolved) | 2 (resolved) | 2 | 2 | 1.158 / 1.152 |
| 2^-6 | 14 | 14 | 14 | 10 (resolved) | 10 (resolved) | 10 (resolved) | none | none | 0.378 / 0.379 |
| 2^-7 | 20 | 20 | 20 | bracket (28, 14) | bracket (28, 14) | bracket [28, 14] | none | none | 0.161 / 0.163 |
| 2^-8 | 28 | 28 | 28 | 56 (resolved) | 56 (resolved) | 56 (resolved) | none | none | 0.075 / 0.076 |
| 2^-9 | 56 | 56 | 56 | 112 (resolved) | 112 (resolved) | 112 (resolved) | none | none | 0.036 / 0.037 |
| 2^-10 | 112 | 112 | 112 | bracket (320, 160) | bracket (320, 160) | bracket [320, 160] | none | none | 0.017 / 0.019 |
| 2^-11 | 160 | 160 | 160 | 500 (resolved) | 500 (resolved) | 500 (resolved) | none | none | 0.009 / 0.011 |

mu_opt exponent (baseline variant): board 0.45413562332058316 (13 pts), L1 7-mu 0.45660270578147155 (13 pts), L1 published 14-mu 0.5106336562283765; board spread (0.36979162999722487, 0.5030358297695823), L1 7-mu spread (0.3710956817205502, 0.5054065471412299)

R3 MSE board vs L1, relative difference over all (S, mu): median -0.09 %, range -0.28 .. +0.28 %

Stall fraction at S = 28 (board): 2^-5: 0.85 %, 2^-6: 1.86 %, 2^-7: 3.57 %, 2^-8: 6.38 %, 2^-9: 11.04 %, 2^-10: 18.87 %, 2^-11: 31.30 %
