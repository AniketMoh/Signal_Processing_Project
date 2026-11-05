#!/bin/bash
# two parallel chains (2 cores)
cd /home/claude/code
( for p in 5 7 9 11; do python3 p6c_surface.py $p A; python3 p6c_surface.py $p B; done; echo done > results/p6c/chainX_done.txt ) > results/p6c/chainX.out 2>&1 &
( for p in 6 8 10; do python3 p6c_surface.py $p A; python3 p6c_surface.py $p B; done; echo done > results/p6c/chainY_done.txt ) > results/p6c/chainY.out 2>&1 &
wait
