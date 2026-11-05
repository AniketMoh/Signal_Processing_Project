# rep2_mathworks.py -- Replication R2: MathWorks example "Equalize a BPSK signal" (ref. 20), re-implemented in numpy.
# Settings copied from the page: 1000 random bits, channel [0.02+0.5j, 0.05], AWGN 30 dB, 8-tap LMS, step 0.1, reference tap 4,
# 200 training symbols, then decision-directed (AdaptAfterTraining = true).
# NOT known from the page (so both options are run and reported): the initial weights ('Auto') and the exact LMS convention.
import numpy as np

def run_once(rng, w_init, nbits=1000, ntrain=200, taps=8, mu=0.1, ref_tap=4, snr_db=30, want_err=False):
    bits = rng.integers(0, 2, nbits)
    x = 1.0 - 2.0 * bits                                   # pskmod(.,2): 0 -> +1, 1 -> -1
    h = np.array([0.02 + 0.5j, 0.05])
    rx = np.convolve(x, h)                                 # length nbits+1 (as conv in MATLAB)
    p = np.mean(np.abs(rx) ** 2)                           # awgn(...,'measured'-style: SNR relative to measured power)
    sigma2 = p / 10 ** (snr_db / 10)
    noise = np.sqrt(sigma2 / 2) * (rng.standard_normal(len(rx)) + 1j * rng.standard_normal(len(rx)))
    rx = rx + noise
    n = nbits                                              # equalise the first nbits samples (as the example does)
    delay = ref_tap - 1                                    # reference tap 4 (1-based) -> desired symbol delayed by 3
    w = np.zeros(taps, dtype=complex)
    if w_init == 'reftap':
        w[delay] = 1.0
    u = np.zeros(taps, dtype=complex)
    err = np.zeros(n)
    dec = np.zeros(n)
    for k in range(n):
        u[1:] = u[:-1]; u[0] = rx[k]
        y = np.vdot(w, u)                                  # w^H u
        d_true = x[k - delay] if k - delay >= 0 else 0.0
        if k < ntrain:
            d = d_true
        else:
            d = 1.0 if y.real >= 0 else -1.0               # decision-directed
        e = d - y
        w = w + mu * np.conj(e) * u                        # complex LMS  w += mu * conj(e) * u   (for y = w^H u)
        err[k] = abs(e)
        dec[k] = 1.0 if y.real >= 0 else -1.0
    # BER on the post-training symbols, compared with the transmitted symbol delayed by `delay`
    idx = np.arange(ntrain, n)
    ref = x[idx - delay]
    ber = np.mean(dec[idx] != ref)
    # convergence: first index where the 20-point moving average of |e| drops below 0.1
    ma = np.convolve(err, np.ones(20) / 20, mode='valid')
    below = np.where(ma < 0.1)[0]
    conv = int(below[0]) + 19 if len(below) else -1
    # unequalised reference: derotate by the channel phase of the main tap and decide on the real part, post-training
    ph = np.angle(h[0])
    raw = (rx[idx] * np.exp(-1j * ph)).real
    ber_raw = np.mean((raw >= 0) != (x[idx] > 0))
    if want_err:
        return err
    return conv, ber, ber_raw, np.mean(err[-100:])

if __name__ == '__main__':
    nrun = 1000
    for w_init in ('zeros', 'reftap'):
        rng = np.random.default_rng(2718)
        res = np.array([run_once(rng, w_init) for _ in range(nrun)])
        conv = res[:, 0]; ok = conv >= 0
        print(f"init={w_init:7s}: runs={nrun}  converged(|e|MA<0.1) {ok.sum()}/{nrun}  "
              f"conv index median {np.median(conv[ok]):.0f}  5-95%: {np.percentile(conv[ok],5):.0f}-{np.percentile(conv[ok],95):.0f}  "
              f"frac of runs with conv<200: {np.mean(conv[ok]<200)*ok.mean():.3f} | post-training BER: mean {res[:,1].mean():.4f}, runs with 0 errors {np.mean(res[:,1]==0):.3f} "
              f"| derotated-unequalised BER (ISI from tap 0.05 only) {res[:,2].mean():.4f} | mean |e| last 100 symbols {res[:,3].mean():.3f}")
