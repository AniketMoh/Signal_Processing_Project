# run_xsim_check.py -- runs tb_lms_rx_syn in the Vivado simulator (xsim) on vectors made by run_lms_syn_tests.py and checks that
# the output file is identical to the L2 golden values (so iverilog and xsim agree).  Level L3.
# Responsible member: Pradeep Kumar (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
#
# Usage (from fpga/sim, after run_lms_syn_tests.py):  python run_xsim_check.py [case ...]
# Vivado location: environment variable VIVADO_BIN, default D:/2025.2/Vivado/bin
import os, shutil, subprocess, sys
import run_lms_syn_tests as t

VIVADO_BIN = os.environ.get("VIVADO_BIN", "D:/2025.2/Vivado/bin")
DEFAULT = ["typical_16_12_nearest_mu2-8", "acc32_mul12_mu2-5_leftshift", "long_NT30000_16_12_mu2-8"]
LOG = os.path.join(t.HERE, "results", "lms_syn_xsim_log.txt")


def tool(name, args, cwd):
    # each argument quoted: cmd.exe would otherwise split "NAME=value" at the '='
    line = " ".join('"%s"' % a for a in [os.path.join(VIVADO_BIN, name + ".bat")] + args)
    return subprocess.run(line, cwd=cwd, capture_output=True, text=True, shell=True)


def main(names):
    cases = {c[0]: c for c in t.CASES}
    lines, ok_all = [], True
    for name in names:
        (_, ba, bm, rnd, p, S, eb, noise, seed, nsym, nt, spacing, _) = cases[name]
        vec = os.path.join(t.BUILD, "vec", name)
        work = os.path.join(t.BUILD, "xsim", name)
        shutil.rmtree(work, ignore_errors=True); os.makedirs(os.path.join(work, "vec"))
        for f in ("r.txt", "d.txt"):                                    # the testbench default DIR is "vec"
            shutil.copy2(os.path.join(vec, f), os.path.join(work, "vec"))
        r = tool("xvlog", [t.TB, t.RTL], work)
        if r.returncode != 0:
            print(name, "xvlog failed", r.stdout[-800:]); ok_all = False; continue
        gens = [f"NSYM={nsym}", f"NT={nt}", f"B_MUL={bm}", f"B_ACC={ba}", f"P={p}", f"RND={rnd}", f"SPACING={spacing}"]
        args = ["tb_lms_rx_syn", "-s", "sim", "-timescale", "1ns/1ps"]
        for g in gens:
            args += ["-generic_top", g]
        r = tool("xelab", args, work)
        if r.returncode != 0:
            print(name, "xelab failed", r.stdout[-800:]); ok_all = False; continue
        r = tool("xsim", ["sim", "-R"], work)
        errs = "ERROR lms_rx_syn" in r.stdout
        a = open(os.path.join(work, "vec", "out_rtl.txt")).read().split()
        b = open(os.path.join(vec, "out_rtl.txt")).read().split()      # iverilog output, already checked against L2
        same = (a == b)
        ok = same and not errs and r.returncode == 0
        msg = f"{name:32s} xsim output identical to iverilog/L2: {same} | budget error: {errs} | {nsym} symbols"
        print(msg); lines.append(msg); ok_all &= ok
    lines.append("ALL PASS" if ok_all else "SOME FAIL"); print(lines[-1])
    with open(LOG, "w") as fh:
        fh.write("# lms_rx_syn.v in Vivado xsim vs the iverilog run (which equals L2), level L3\n" + "\n".join(lines) + "\n")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or DEFAULT))
