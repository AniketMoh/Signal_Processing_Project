# gen_noise_vectors.py -- golden data for the lfsr_noise RTL test.
# 1) builds the 12 start values exactly as fxp_lib.lfsr_noise does (numpy default_rng(seed), one value per LFSR)
# 2) computes the integer noise stream in plain Python (golden_noise.txt)
# 3) checks that this integer stream equals fxp_lib._lfsr_noise (the L2 model, float output) exactly
import sys
sys.path.insert(0, '..')
import numpy as np
from fxp_lib import LFSR_TAPS, _lfsr_noise

SEED = 4242
NS = 20000
rng = np.random.default_rng(SEED)
states = [int(rng.integers(1, (1 << int(t[0])) - 1)) for t in LFSR_TAPS]
with open('seeds.hex', 'w') as f:
    for s in states:
        f.write('%09x\n' % s)

st = list(states)
out = []
for i in range(NS):
    total = 0
    for j in range(12):
        n = int(LFSR_TAPS[j, 0]); k = int(LFSR_TAPS[j, 1])
        word = 0
        s = st[j]
        for b in range(16):
            bit = s & 1
            word = (word << 1) | bit
            fb = ((s >> 0) ^ (s >> (n - k))) & 1
            s = (s >> 1) | (fb << (n - 1))
        st[j] = s
        total += word
    out.append(total - 393210)
np.savetxt('golden_noise.txt', np.array(out, dtype=np.int64), fmt='%d')

# cross-check with the L2 model
ref = _lfsr_noise(NS, LFSR_TAPS, np.array(states, np.int64))      # float, = (sum (word+0.5)/65536) - 6
ok = np.array_equal(np.round(ref * 65536).astype(np.int64), np.array(out, dtype=np.int64))
print('integer reference equals fxp_lib._lfsr_noise (x 65536):', ok, ' min/max', min(out), max(out))
