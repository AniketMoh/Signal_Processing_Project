# rep6b_exact_check.py -- the small-step formula is only a first-order result.  Here the gradient-noise term is replaced by its exact value
# for white Gaussian input, J_min*g/(1-g) with g = mu*N/(2-mu) (stationary LMS theory, Widrow-type), keeping the lag term unchanged.
# This is a check of WHY the simple formula drifts at large mu, not a new claim from the papers.
import numpy as np
import rep6_tracking_theory as r
res = np.load('results/rep6_curves.npy', allow_pickle=True).item()
N, SV2 = r.N, r.SV2
fine = np.geomspace(0.0003, 0.2, 4000)
print("kind xi | mu_opt sim | small-step theory | refined theory | sim/small-step | sim/refined")
for kind in (0, 1):
    xs, ms, mt, mr = [], [], [], []
    for xi in [0.0002, 0.0005, 0.001, 0.002, 0.004, 0.008]:
        mus, sim, th = res[str((kind, xi))]
        g = fine * N / (2 - fine)
        lag = xi ** 2 / (2 * fine) if kind == 0 else xi ** 2 / fine ** 2
        ref = SV2 * g / (1 - g) + lag
        mu_r = fine[int(np.argmin(ref))]
        mu_s, _ = r.refine_min(mus, sim)
        mu_t = (xi / np.sqrt(SV2 * N)) if kind == 0 else (4 * xi ** 2 / (N * SV2)) ** (1 / 3)
        xs.append(xi); ms.append(mu_s); mt.append(mu_t); mr.append(mu_r)
        print(f"{kind}  {xi:.4f} | {mu_s:.5f} | {mu_t:.5f} | {mu_r:.5f} | {mu_s/mu_t:.3f} | {mu_s/mu_r:.3f}")
    print(f"   exponent: sim {np.polyfit(np.log(xs), np.log(ms), 1)[0]:.3f}, small-step theory {np.polyfit(np.log(xs), np.log(mt), 1)[0]:.3f}, refined theory {np.polyfit(np.log(xs), np.log(mr), 1)[0]:.3f}")
