"""Independent re-implementation of the P5 link, written from the specification (plain numpy, no lms_lib / exp_lib).
Own random training bits and own noise.  Checks (1) BER recomputed from the delivered WAV files, (2) measured noise level vs 14 dB,
(3) BER of R1/R2/R3 for S = 28 and static with a separate implementation (statistical agreement expected, not identical errors)."""
import numpy as np, sys
from scipy.io import wavfile
P="/home/claude/code/results/p5/"
fs,orig=wavfile.read(P+"original_8k.wav"); bits=np.unpackbits(orig).astype(int)
print("original_8k.wav:",fs,"Hz,",len(orig),"samples,",len(bits),"bits")
# (1) BER recomputed from the delivered WAV files
for sc in ("static","slow_S1000","boundary_S28","fast_S1"):
    row=[]
    for rx in ("R1","R2","R3"):
        _,rec=wavfile.read(P+f"{sc}_{rx}.wav"); b=np.unpackbits(rec).astype(int); row.append(f"{rx} errors {int(np.sum(b!=bits)):6d}")
    print(f"WAV check {sc:14s}"," | ".join(row))
# (2),(3) independent simulation
EB=14.0; sigma=np.sqrt(1/(2*10**(EB/10))); L=16; D=2; mu=2.0**-8; NT=30000; DA=2.0**-7
def run(S,seed):
    rng=np.random.default_rng(seed)
    x=np.concatenate([2*rng.integers(0,2,NT)-1, 2*bits-1, 2*rng.integers(0,2,16)-1]).astype(float); N=len(x)
    c=np.full(N,40)
    if S is not None:
        k=(np.arange(NT,N)-NT)//S; idx=k%(2*76); c[NT:]=40+np.where(idx<=76,idx,152-idx)
    a=c*DA; xp=np.concatenate([[0,0],x])                   # x[n-1], x[n-2] with zero history
    clean=x+a*xp[1:-1]+0.1*xp[:-2]; noise=sigma*rng.standard_normal(N); r=clean+noise
    d=np.concatenate([[0]*D,x[:-D]])                       # desired = x[n-D]
    w=np.zeros(L); wf=None; u=np.zeros(L); yA=np.zeros(N); yF=np.zeros(N)
    for n in range(N):
        u[1:]=u[:-1]; u[0]=r[n]
        if n==NT: wf=w.copy()
        y=w@u; yA[n]=y; yF[n]=y if wf is None else wf@u
        w=w+mu*(d[n]-y)*u                                  # supervised LMS, error uses the known bit
    nb=len(bits); j=np.arange(nb)
    est={"R1":(r[NT+j]>=0),"R2":(yF[NT+j+D]>=0),"R3":(yA[NT+j+D]>=0)}
    return {k:int(np.sum(v.astype(int)!=bits)) for k,v in est.items()}, float(np.var(noise)), sigma**2
for S in (None,1000,28,1):
    res=[run(S,seed) for seed in (11,12)]
    print(f"independent sim S={S}: errors per run (2 runs) ", [r[0] for r in res], " measured noise var %.5f, expected %.5f"%(res[0][1],res[0][2]))
