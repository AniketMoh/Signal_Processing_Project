cd /home/claude/code
for t in T5 T3 T2 T6 T4; do python3 p6a_tests.py $t > results/p6a/${t}_console.txt 2>&1; done
echo done > results/p6a/chain_C_done.txt
