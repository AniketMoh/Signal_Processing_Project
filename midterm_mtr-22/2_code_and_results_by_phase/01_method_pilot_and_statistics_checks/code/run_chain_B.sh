cd /home/claude/code
python3 final_sweep.py primary 12 > /dev/null 2>&1
python3 final_sweep.py primary 14 ber14 > /dev/null 2>&1
echo CHAIN_B_DONE > results/chain_B_done.txt
