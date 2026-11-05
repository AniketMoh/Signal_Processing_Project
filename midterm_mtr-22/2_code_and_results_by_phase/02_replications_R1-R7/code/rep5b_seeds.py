# rep5b_seeds.py -- seed-to-seed spread of the Ghanassi replication at four step sizes (different input seed AND different random w_o each time)
import numpy as np
import rep5_ghanassi as g
print("mu  variant  xi' for 5 independent (seed, w_o) pairs | mean | std/mean")
for mu in (0.002, 0.01, 0.04, 0.075, 0.16):
    for acc in (0, 1):
        vals = []
        for s in range(5):
            wo = np.random.default_rng(100 + s).standard_normal(g.N); wo *= np.sqrt(g.WO2) / np.linalg.norm(wo)
            vals.append(g.sim(mu, 12_000_000, 3_000_000, bool(acc), 5000 + 10 * s + acc, wo))
        v = np.array(vals)
        print(f"{mu:6.3f} {'acc' if acc else 'noacc':5s} " + " ".join(f"{x:.3e}" for x in v) + f" | {v.mean():.3e} | {v.std()/v.mean():.3f}", flush=True)
