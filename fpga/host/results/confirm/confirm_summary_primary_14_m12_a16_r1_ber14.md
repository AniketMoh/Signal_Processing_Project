# Mid-term findings re-measured on the Boolean Board (L5) vs the mid-term simulation (L1)

Board: supervised LMS, LFSR sum-of-uniforms noise, fixed point of the loaded build. L1: float, Gaussian noise. Same grid, rules and analysis code (sweep_analyse.analyse, unchanged); L1 restricted to the same 7 step sizes and seeds.

## primary channel, 14 dB, build m12_a16_r1_ber14, 1500 seeds

| mu | S*_MSE board | S*_MSE L1 (same mu) | S*_MSE L1 published | S*_BER board | S*_BER L1 | S*_BER L1 published | S_cross board | S_cross L1 | static eps board / L1 |
|---|---|---|---|---|---|---|---|---|---|
| 2^-7 | 20 | 20 | 20 | bracket (56, 28) | 40 (resolved) | 40 (resolved) | none | none | 0.164 / 0.164 |
| 2^-8 | 28 | 28 | 28 | bracket (160, 80) | 112 (resolved) | 112 (resolved) | none | none | 0.077 / 0.076 |
| 2^-9 | 56 | 56 | 56 | bracket (320, 160) | bracket (320, 160) | bracket [320, 160] | none | none | 0.037 / 0.037 |
| 2^-10 | 112 | 112 | 112 | bracket (1000, 320) | bracket (1000, 320) | bracket [1000, 320] | none | none | 0.018 / 0.018 |
| 2^-11 | 224 | 224 | 224 | bracket (2000, 500) | bracket (2000, 500) | bracket [2000, 500] | none | none | 0.012 / 0.011 |

mu_opt exponent (baseline variant): board 0.5540472306629546 (8 pts), L1 7-mu 0.5621117541502475 (8 pts), L1 published 14-mu 0.5787539563033651; board spread (0.5212233453331399, 0.5602280915970891), L1 7-mu spread (0.5216611604168706, 0.5713486686962754)

R3 MSE board vs L1, relative difference over all (S, mu): median +0.02 %, range -0.03 .. +0.37 %

Stall fraction at S = 28 (board): 2^-7: 4.01 %, 2^-8: 7.05 %, 2^-9: 12.13 %, 2^-10: 20.73 %, 2^-11: 34.25 %
