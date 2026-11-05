"""E-1 validation, analysis part.  2000 seeds = 40 independent replicate experiments of 50 seeds each.
'Truth' = value pooled over all 2000 seeds.  For each replicate the paired seed-level bootstrap (B = 2000) gives a 95 % interval;
we count how often it contains the truth (nominal 95 %) and compare the average bootstrap standard deviation with the actual spread of the
replicate estimates (ratio ~ 1 means the bootstrap gets the uncertainty right).  The same is done for the sensitivity methods for BER_R3
(plain Wilson, burst-adjusted Wilson).  Run: python3 validate_bootstrap_analyse.py"""
import numpy as np
from sweep_analyse import paired_ratio, resample_counts, interp_matrix, wilson, burst_wilson
from freeze_grids import STATIC_C
A_ = np.load("results/validate_bootstrap_A.npz"); B_ = np.load("results/validate_bootstrap_B.npz")
get = lambda k: np.concatenate([A_[k], B_[k]], axis=-1)
cg = np.array(STATIC_C); cs = np.arange(40, 117); Am = interp_matrix(cg, cs); NREP, PER = 40, 50
rng = np.random.default_rng(11); W = resample_counts(PER, 2000, rng)
lines = []
def lg(s): print(s); lines.append(s)
lg("Validation of the paired seed-level bootstrap (12 dB, primary channel, 40 replicates x 50 seeds, seeds 300000-301999; L1 validation data)")
for i, mu in enumerate((2.0 ** -5, 2.0 ** -8)):
    K = np.array([get(f"static_c{c}|E3")[i] for c in STATIC_C]).astype(float)        # [node, seed]
    n_node = 152000.0
    for S in (20, 1000):
        E3 = get(f"{S}|E3")[i].astype(float); Bu = get(f"{S}|B3_20")[i].astype(float); cw = A_[f"{S}|c_win"].astype(int)
        n_traj = len(cw); w = np.bincount(cw - 40, minlength=77) / n_traj
        # truth from all 2000 seeds, for both interpolation methods (each replicate chooses its method from its own data, as the analysis does)
        b3_true = E3.sum() / (len(E3) * n_traj)
        pK = K.sum(axis=1) / (K.shape[1] * n_node)
        truth = {"log": b3_true / (np.exp(np.log(pK) @ Am.T) @ w), "lin": b3_true / ((pK @ Am.T) @ w)}
        method = "log"; r_true = truth["log"]; nlog = 0
        cov = dict(boot=0, plain=0, burst=0, bootb3=0); est_r, est_b3, sd_boot, sd_plain, sd_burst, sd_bootb3, kk = [], [], [], [], [], [], []
        for r in range(NREP):
            sl = slice(r * PER, (r + 1) * PER)
            m_r = "log" if np.all(K[:, sl].sum(axis=1) > 0) else "lin"; nlog += m_r == "log"
            pr, lo, hi, sd, _ = paired_ratio(E3[sl], n_traj, K[:, sl], n_node, Am, w, m_r, W)
            est_r.append(pr / truth[m_r]); sd_boot.append(sd / truth[m_r]); cov["boot"] += lo <= truth[m_r] <= hi
            k = E3[sl].sum(); N = PER * n_traj; C = Bu[sl].sum(); kk.append(k)
            l1, u1 = wilson(k, N); l2, u2 = burst_wilson(k, C, N)
            cov["plain"] += l1 <= b3_true <= u1; cov["burst"] += l2 <= b3_true <= u2
            b3b = (W @ E3[sl]) / N; q = np.percentile(b3b, [2.5, 97.5]); cov["bootb3"] += q[0] <= b3_true <= q[1]
            est_b3.append(k / N); sd_plain.append((u1 - l1) / 3.92); sd_burst.append((u2 - l2) / 3.92); sd_bootb3.append(b3b.std(ddof=1))
        e_r, e_b = np.std(est_r, ddof=1), np.std(est_b3, ddof=1)
        lg(f"\n mu=2^{np.log2(mu):.0f}  S={S}  (log interpolation in {nlog}/{NREP} replicates, linear otherwise):  true ratio {r_true:.3f} (linear-interp. truth {truth['lin']:.3f})  (R3 BER {b3_true:.2e}, ref {b3_true/r_true:.2e}; ~{np.mean(kk):.0f} R3 errors per replicate, mean burst size {E3.sum()/max(Bu.sum(),1):.2f})")
        lg(f"   ratio (PRIMARY, paired bootstrap): coverage {cov['boot']}/{NREP};  mean bootstrap SD / actual SD of replicate ratios (both relative to truth) = {np.mean(sd_boot)/e_r:.2f}")
        lg(f"   R3 BER alone: coverage  plain Wilson {cov['plain']}/{NREP}  burst Wilson {cov['burst']}/{NREP}  seed bootstrap {cov['bootb3']}/{NREP}")
        lg(f"                 SD ratio (method / actual): plain Wilson {np.mean(sd_plain)/e_b:.2f}  burst Wilson {np.mean(sd_burst)/e_b:.2f}  seed bootstrap {np.mean(sd_bootb3)/e_b:.2f}")
        # benefit of pairing: correlation between per-seed trajectory errors and the per-seed reference
        refseed = ((K / n_node).T @ Am.T) @ w
        lg(f"   per-seed correlation trajectory R3 errors vs static reference (pairing benefit): {np.corrcoef(E3, refseed)[0,1]:+.3f}")
open("results/validate_bootstrap_log.txt", "w").write("\n".join(lines))
