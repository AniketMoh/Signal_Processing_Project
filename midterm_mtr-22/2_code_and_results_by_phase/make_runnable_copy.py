# Copies every file of this package back into the folder layout the scripts expect
# (scripts import each other and read/write "results/..." relative paths).
# Usage, from this folder:   python3 make_runnable_copy.py
# Result: a folder "runnable_code/"; run any script from inside it, e.g.
#   cd runnable_code && python3 report_figs.py
import csv, os, shutil

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "runnable_code")
count = 0
with open(os.path.join(here, "manifest.csv")) as fh:
    for row in csv.DictReader(fh):
        src = os.path.join(here, row["location_in_this_package"])
        dst = os.path.join(out, row["original_path_in_runnable_layout"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
print("copied", count, "files into", out)
