% mathworks_crosscheck.m -- MATLAB cross-check of the Python model (replication R2 and the PPR's MathWorks cross-check).
% Run in MATLAB R2019a or later. Parts 1-2 need the Communications Toolbox; Part 3 needs plain MATLAB only.
% Put this file and xcheck_c40.csv, xcheck_c116.csv in the same folder, cd to it, and type:  mathworks_crosscheck
% Copy the whole Command Window output back.  Python reference values are printed next to each MATLAB value.

%% Part 1 -- the MathWorks example "Equalize a BPSK signal", repeated 1000 times (replication R2)
rng(1);
nrun = 1000; convIdx = -ones(nrun,1); nerr = zeros(nrun,1);
for k = 1:nrun
    data = randi([0 1],1000,1); modData = pskmod(data,2);            % bit 0 -> +1, bit 1 -> -1
    rxSig = awgn(conv(modData,[0.02+0.5i; 0.05]),30);                % channel and SNR of the example
    lineq = comm.LinearEqualizer('NumTaps',8,'StepSize',0.1,'Constellation',complex([-1 1]),'ReferenceTap',4);
    [eqSig,err] = lineq(rxSig(1:1000), modData(1:200));              % 200 training symbols, then decision-directed
    ma = movmean(abs(err),[19 0]); idx = find(ma(20:end) < 0.1, 1);  % 20-symbol moving average of |e| below 0.1
    if ~isempty(idx), convIdx(k) = idx + 19 - 1; end                 % 0-based symbol index, as in rep2_mathworks.py
    dec = real(eqSig(201:1000)) < 0;                                 % equalizer output is delayed by ReferenceTap-1 = 3
    nerr(k) = sum(dec ~= data((201:1000)-3));
end
ok = convIdx >= 0;
fprintf('\nPART 1  MathWorks example, %d runs\n', nrun);
fprintf('  MATLAB: median convergence %g symbols (5-95%%: %g-%g); converged under 200: %d/%d; runs with 0 post-training errors: %d/%d\n', ...
    median(convIdx(ok)), prctile(convIdx(ok),5), prctile(convIdx(ok),95), sum(ok & convIdx<200), nrun, sum(nerr==0), nrun);
fprintf('  Python: median 108 symbols (5-95%%: 97-123); converged under 200: 1000/1000; runs with 0 post-training errors: 1000/1000\n');

%% Part 2 -- MATLAB's own LMS equalizer on OUR received samples (static primary channel, 14 dB, mu = 2^-8, 16 taps)
% The alignment convention of comm.LinearEqualizer is not documented precisely, so every reference tap 1..6 is tried;
% the correct one gives the smallest MSE and should be close to the Python value.
pyMSE = containers.Map({40,116},{0.022469,0.055690});
fprintf('\nPART 2  comm.LinearEqualizer (LMS, 16 taps, step 2^-8) on xcheck_c40.csv / xcheck_c116.csv\n');
for c0 = [40 116]
    M = readmatrix(sprintf('xcheck_c%d.csv', c0)); r = M(:,1); d = M(:,2);   % d(n) = x(n-2), so x(n) = d(n+2)
    x = d(3:end);
    best = inf; bestTap = 0;
    for tap = 1:6
        eqz = comm.LinearEqualizer('Algorithm','LMS','NumTaps',16,'StepSize',2^-8,'Constellation',complex([-1 1]), ...
                                   'ReferenceTap',tap,'AdaptAfterTraining',false);
        [~, e] = eqz(complex(r), complex(x));
        m = mean(abs(e(30001:numel(x))).^2);
        fprintf('  c = %3d, ReferenceTap %d: MATLAB MSE = %.6f\n', c0, tap, m);
        if m < best, best = m; bestTap = tap; end
    end
    fprintf('  c = %3d: best MATLAB MSE %.6f (ReferenceTap %d)  |  Python MSE %.6f  |  ratio %.4f\n', c0, best, bestTap, pyMSE(c0), best/pyMSE(c0));
end

%% Part 3 -- the same LMS written out in plain MATLAB (no toolbox), on the same samples: must match Python almost exactly
% y(n) = w'u(n) with u(n) = [r(n) ... r(n-15)], e(n) = d(n) - y(n), w <- w + mu e(n) u(n)  (d(n) = x(n-2), i.e. Delta = 2)
fprintf('\nPART 3  plain-MATLAB LMS (same equations as the Python model)\n');
for c0 = [40 116]
    M = readmatrix(sprintf('xcheck_c%d.csv', c0)); r = M(:,1); d = M(:,2);
    L = 16; mu = 2^-8; N = numel(r); w = zeros(L,1); u = zeros(L,1); e = zeros(N,1);
    for n = 1:N
        u = [r(n); u(1:L-1)];
        y = w.' * u; e(n) = d(n) - y;
        w = w + mu * e(n) * u;
    end
    m = mean(e(30001:N).^2);
    fprintf('  c = %3d: MATLAB MSE %.6f  |  Python MSE %.6f  |  ratio %.5f\n', c0, m, pyMSE(c0), m/pyMSE(c0));
    fprintf('          MATLAB first 5 weights at the end: %s\n', sprintf('%.5f ', w(1:5)));
end
fprintf('          Python, same loop, final weights: c=40: 0.00313 0.02066 0.97648 -0.30794 0.00031; c=116: -0.04735 0.07760 0.88539 -0.77405 0.58270\n');
fprintf('\nDone. Copy everything above back.\n');
