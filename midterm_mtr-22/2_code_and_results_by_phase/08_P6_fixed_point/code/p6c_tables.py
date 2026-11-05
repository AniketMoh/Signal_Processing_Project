# p6c_tables.py -- tables of the P6 word-length surface (results/p6c/surface_<fam>_<p>.json), level L2, 16 dB, 20 seeds.
# Entry = S*_MSE (rho_th = 0.5; the fastest S in the grid at which R3 still passes);  'undef' = rho undefined because the static excess of
# that configuration already exceeds the plateau (the filter does not work even on a static channel);  '-' = not run.
import json, os, numpy as np
L1 = {5: 14, 6: 10, 7: 20, 8: 28, 9: 56, 10: 112, 11: 224}    # final L1 S*_MSE, primary 16 dB (RESULTS_FINAL_L1.md, Table 1); 2^-11 checked below
out = open("results/p6c/tables.md", "w")
def w(s): print(s); out.write(s + "\n")
for fam, title, keyfmt, configs in (
    ("A", "Family A: accumulator width (B_mul = min(12, B_acc))", "{ba}|{bm}|{rnd}", [(ba, min(12, ba)) for ba in (26, 16, 14, 12, 10)]),
    ("B", "Family B: multiplier (coefficient) width, B_acc = 26", "{ba}|{bm}|{rnd}", [(26, bm) for bm in (16, 12, 8)])):
    for rnd in (1, 0):
        w(f"\n### {title}, {'round to nearest' if rnd else 'truncation'}\n")
        w("| B_acc / B_mul | " + " | ".join(f"2^-{p}" for p in range(5, 12)) + " |")
        w("|---|" + "---|" * 7)
        for ba, bm in configs:
            row = []
            for p in range(5, 12):
                fn = f"results/p6c/surface_{fam}_{p}.json"
                if not os.path.exists(fn): row.append("-"); continue
                r = json.load(open(fn)).get(f"{ba}|{bm}|{rnd}")
                if r is None: row.append("-"); continue
                row.append("undef" if "u" in r["status"] else str(r["S_star"]))
            w(f"| {ba} / {bm} | " + " | ".join(row) + " |")
w("\nL1 reference S*_MSE (primary, 16 dB, 100 seeds): " + ", ".join(f"2^-{p}: {v}" for p, v in L1.items()))
