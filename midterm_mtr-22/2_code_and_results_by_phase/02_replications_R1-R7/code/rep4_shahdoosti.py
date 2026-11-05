# rep4_shahdoosti.py -- Replication R4: stalling of fixed-point LMS, Shahdoosti (arXiv 1807.07395), Sec. on the stalling effect.
# Setup read from the paper: AR(10) signal u(i) = 0.1*(u(i-1)+...+u(i-10)), initial u(1:10) = [0.2 0.3 0.28 0.26 0.4 0.24 0.46 0.6 0.56 0.48],
# initial weights 0.01, mu = 0.01, 12 fractional bits (LSB = 2^-12), rounding to the nearest LSB, no noise.
# Paper's claims: threshold e_T = LSB/(2*mu*u) (=0.0244 for u = 0.5), and stalling begins at iteration about 134.
# The paper does not say how the desired signal is built; reading used here: one-step linear prediction, d(i) = u(i), regressor = the 10 past samples.
import numpy as np

LSB = 2.0 ** -12
mu = 0.01
u0 = [0.2, 0.3, 0.28, 0.26, 0.4, 0.24, 0.46, 0.6, 0.56, 0.48]

def run(quantised, n_iter=600, regressor='past10'):
    u = list(u0)
    w = np.full(10, 0.01)
    if quantised:
        w = np.round(w / LSB) * LSB
    first_zero_update = None
    log = []
    for i in range(10, 10 + n_iter):
        reg = np.array(u[i - 10:i][::-1])                  # u(i-1), ..., u(i-10)
        d = 0.1 * np.sum(reg)                              # AR signal value = desired output
        y = np.dot(w, reg)
        e = d - y
        upd = mu * e * reg
        if quantised:
            upd = np.round(upd / LSB) * LSB                # rounds to the nearest LSB; <0.5 LSB -> 0
        w = w + upd
        u.append(d)
        nz = int(np.count_nonzero(upd))
        log.append((i - 9, e, nz, np.max(np.abs(mu * e * reg)) / LSB))
        if quantised and nz == 0 and first_zero_update is None:
            first_zero_update = i - 9                      # iteration number (1-based) of the first iteration with all updates rounded to 0
    return log, first_zero_update, w

if __name__ == '__main__':
    print("threshold from the paper's example: LSB/(2*mu*0.5) =", LSB / (2 * mu * 0.5))
    logf, _, wf = run(False)
    logq, first, wq = run(True)
    print("float LMS: |e| at iterations 50,100,134,200,400,600:", [round(abs(logf[k - 1][1]), 5) for k in (50, 100, 134, 200, 400, 600)])
    print("quantised LMS: |e| at the same iterations:           ", [round(abs(logq[k - 1][1]), 5) for k in (50, 100, 134, 200, 400, 600)])
    print("first iteration with all 10 updates rounded to zero (quantised):", first)
    # count of updated taps per iteration around the stall
    for k in list(range(100, 200, 10)):
        print(f"  iter {k}: |e|={abs(logq[k-1][1]):.4f}, taps updated={logq[k-1][2]}, max |mu e u|/LSB={logq[k-1][3]:.2f}")
    # the paper's inequality, checked per tap at the stall: |mu e u_i| < LSB/2  <=>  |e| < LSB/(2 mu |u_i|)
    k = first
    print("final |e| (quantised) =", abs(logq[-1][1]), " final |e| (float) =", abs(logf[-1][1]))
    print("floor of the quantised error after the stall: sum(w)=", wq.sum(), "(ideal sum 1.0)")
