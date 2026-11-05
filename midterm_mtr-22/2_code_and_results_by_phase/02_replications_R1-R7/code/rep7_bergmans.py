# R7: Bergmans (1990), LMS identification of a channel with gain variations.
# Rebuilds the simulations of his Figs. 2-4 and compares them with Eqs. (10) and (27).
# System: r_k = x_k^T f (1 + g_k) + n_k,  g_k = beta*z_k + (1-beta)*g_{k-1}
# Filter: c_{k+1} = c_k + mu * e_k * x_k,  e_k = r_k - x_k^T c_k
# Excess error eps = E[(e_k - n_k)^2], reported as eps/N0 in dB.
# Paper settings (Sec. V): M = 5, f0 = 1, f2 = -1, binary input, Gaussian n and z,
# c_0 = f, 16384 samples per mu, time averages.

import numpy as np

M = 5
f = np.array([1.0, 0.0, -1.0, 0.0, 0.0])
f2 = np.sum(f ** 2)          # |f|^2 = 2
N_SAMPLES = 16384            # as in the paper
N_RUNS = 20                  # independent runs; the paper used one time average
mus = 2.0 ** np.arange(-15, -1.49, 0.5)
betas = [0.1, 0.01]

# (figure, SNR in dB, gain variation in % rms)
cases = [("Fig. 2", 20, 2), ("Fig. 3", 25, 2), ("Fig. 4", 20, 5)]


def theory(mu, beta, G, N0):
    eps_g = mu * M * N0 / (2 - mu * M)                                   # Eq. (10)
    eps_l = G * f2 * beta / ((1 - mu / 2) * (beta + (1 - beta) * mu))    # Eq. (27)
    return eps_g + eps_l


def theory_lag_in_gradient(mu, beta, G, N0):
    # diagnostic only: the lag error also drives gradient noise, so N0 -> N0 + eps_l in Eq. (10)
    eps_l = G * f2 * beta / ((1 - mu / 2) * (beta + (1 - beta) * mu))
    return mu * M * (N0 + eps_l) / (2 - mu * M) + eps_l


def simulate(mu, beta, G, N0, seed):
    rng = np.random.default_rng(seed)
    x = rng.choice([-1.0, 1.0], size=(N_RUNS, N_SAMPLES + M))
    n = rng.normal(0, np.sqrt(N0), size=(N_RUNS, N_SAMPLES))
    z = rng.normal(0, np.sqrt((2 - beta) * G / beta), size=(N_RUNS, N_SAMPLES))
    g = rng.normal(0, np.sqrt(G), size=N_RUNS)       # start g in its steady state
    c = np.tile(f, (N_RUNS, 1))                      # c_0 = f, as in the paper
    total = np.zeros(N_RUNS)
    for k in range(N_SAMPLES):
        g = beta * z[:, k] + (1 - beta) * g
        xk = x[:, k:k + M][:, ::-1]                  # [x_k, x_{k-1}, ..., x_{k-M+1}]
        excess = np.sum(xk * (f[None, :] * (1 + g[:, None]) - c), axis=1)
        e = excess + n[:, k]
        c = c + mu * e[:, None] * xk
        total += excess ** 2
    return total / N_SAMPLES                         # time average per run


if __name__ == "__main__":
    results = {}
    lines = []
    for name, snr_db, rms in cases:
        G = (rms / 100) ** 2
        N0 = f2 * (1 + G) / 10 ** (snr_db / 10)      # Eq. (6)
        for beta in betas:
            sim, th, spread = [], [], []
            for i, mu in enumerate(mus):
                eps = simulate(mu, beta, G, N0, seed=7000 + i)
                sim.append(np.mean(eps) / N0)
                spread.append(np.std(10 * np.log10(eps / N0)))
                th.append(theory(mu, beta, G, N0) / N0)
            sim, th = np.array(sim), np.array(th)
            th2 = np.array([theory_lag_in_gradient(mu, beta, G, N0) for mu in mus]) / N0
            diff = 10 * np.log10(sim / th)
            diff2 = 10 * np.log10(sim / th2)
            results[(name, beta)] = dict(mu=mus, sim=sim, th=th, spread=np.array(spread))
            # Eq. (32): monotone if 2P < Q^2, else a minimum
            P = G * 10 ** (snr_db / 10) * beta * M / (1 + G)
            Q = beta * M
            kind = "minimum" if 2 * P > Q ** 2 else "monotone"
            imin = np.argmin(sim)
            line = (f"{name} SNR={snr_db} dB, G={rms}% rms, beta={beta}: "
                    f"sim-theory {diff.min():+.2f} to {diff.max():+.2f} dB "
                    f"(max |diff| {np.abs(diff).max():.2f} dB), single-run spread {np.mean(spread):.2f} dB; "
                    f"Eq.32 predicts {kind}; sim minimum at mu=2^{np.log2(mus[imin]):.1f}, "
                    f"theory minimum at mu=2^{np.log2(mus[np.argmin(th)]):.1f}; "
                    f"minimum depth below small-mu level: sim {10*np.log10(sim[0]/sim.min()):.2f} dB, "
                    f"theory {10*np.log10(th[0]/th.min()):.2f} dB; "
                    f"with lag in gradient noise: {diff2.min():+.2f} to {diff2.max():+.2f} dB")
            print(line)
            lines.append(line)
    np.save("results/rep7_bergmans.npy", results, allow_pickle=True)
    with open("results/rep7_log.txt", "w") as fh:
        fh.write("\n".join(lines) + "\n")
