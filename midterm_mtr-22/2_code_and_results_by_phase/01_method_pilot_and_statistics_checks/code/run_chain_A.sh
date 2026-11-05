cd /home/claude/code
python3 final_sweep.py primary 16 > /dev/null 2>&1
python3 final_sweep.py primary 14 > /dev/null 2>&1
python3 final_sweep.py control 16 > /dev/null 2>&1
python3 final_sweep.py control 14 > /dev/null 2>&1
python3 p2_final.py 16 > results/p2_final_16dB_console_log.txt 2>&1
python3 p2_final.py 14 > results/p2_final_14dB_console_log.txt 2>&1
echo CHAIN_A_DONE > results/chain_A_done.txt
