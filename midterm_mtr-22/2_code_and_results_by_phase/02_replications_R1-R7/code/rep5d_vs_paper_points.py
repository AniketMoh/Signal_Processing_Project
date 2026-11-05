# rep5d_vs_paper_points.py -- compares the corrected R5 simulation (rep5c, two quantisers) with the paper's OWN simulation points,
# digitised from Ghanassi et al. (2007) Figs. 2 and 3 (red circles; axis calibration from the decade labels; reading error about +-5 %).
# Runs the simulation at the paper's step sizes (same seeds, N, b, w_o, iterations as rep5c).
import numpy as np
from rep5c_ghanassi_fulltext import sim2, N, WO2
paper = {0: [(0.0010, 1.13e-05), (0.0020, 2.79e-06), (0.0030, 1.20e-06), (0.0050, 4.24e-07), (0.0101, 9.59e-08), (0.0204, 2.48e-08),
             (0.0308, 1.47e-08), (0.0413, 1.89e-08), (0.0519, 2.33e-08), (0.0623, 3.12e-08), (0.0730, 3.72e-08), (0.0836, 4.39e-08),
             (0.0942, 5.12e-08), (0.1046, 5.96e-08), (0.1155, 6.22e-08), (0.1259, 6.67e-08), (0.1370, 8.24e-08), (0.1529, 1.06e-07),
             (0.1690, 1.58e-07), (0.1800, 2.58e-07), (0.1904, 5.19e-07)],
         1: [(0.0010, 1.13e-05), (0.0020, 2.84e-06), (0.0030, 1.25e-06), (0.0051, 4.03e-07), (0.0102, 9.68e-08), (0.0206, 2.53e-08),
             (0.0311, 1.04e-08), (0.0416, 6.38e-09), (0.0522, 4.84e-09), (0.0626, 3.09e-09), (0.0733, 7.15e-09), (0.0839, 1.73e-08),
             (0.0943, 3.01e-08), (0.1050, 4.03e-08), (0.1210, 4.05e-08), (0.1373, 5.55e-08), (0.1529, 6.84e-08), (0.1690, 1.02e-07),
             (0.1801, 1.86e-07), (0.1904, 3.59e-07)]}
if __name__ == '__main__':
    rng = np.random.default_rng(1234); wo = rng.standard_normal(N); wo *= np.sqrt(WO2) / np.linalg.norm(wo)
    n_iter = 4_000_000; rows = []
    print("variant | mu | paper (digitised) | ours | ours/paper")
    for acc in (0, 1):
        for mu, pv in paper[acc]:
            xi = sim2(mu, n_iter, n_iter // 4, bool(acc), 777 + acc, wo)
            rows.append((acc, mu, pv, xi))
            print(f"{'acc' if acc else 'noacc':5s} | {mu:.4f} | {pv:.2e} | {xi:.2e} | {xi/pv:.2f}", flush=True)
    np.save('results/rep5d_vs_paper.npy', np.array(rows))
