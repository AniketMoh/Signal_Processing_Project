P5 recorded-audio demonstration (owner's voice recording)
Level L1 simulation: floating point, ideal Gaussian noise, Eb/N0 14 dB, mu 2^-8, primary channel c 40-116.
MODE: SUPERVISED LMS. The adaptive receiver R3 uses the KNOWN transmitted bits as its reference during training and during the payload (software experiment only).
R1 = direct detector, R2 = equalizer frozen after training, R3 = adaptive LMS equalizer. All three see the same received samples.
Files: original_8k.wav (converted original), <scenario>_R1/R2/R3.wav (reconstructions), p5_metrics.json, fig_P5_audio.png.
