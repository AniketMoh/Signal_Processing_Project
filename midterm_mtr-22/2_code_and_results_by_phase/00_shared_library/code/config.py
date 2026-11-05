# config.py -- every project parameter lives here (floating-point level L1)
# Status of each value is written next to it: APPROVED, PROVISIONAL (to be frozen at FREEZE-1), or FIXED.

DA = 2.0 ** -7            # channel coefficient increment per update   (APPROVED, P-03)

CFG = {
    "L": 16,              # equalizer length                           (PROVISIONAL, project decision 20 Oct)
    "M": 3,               # channel length (taps)                      (FIXED)
    "h2": 0.1,            # third channel tap, kept constant           (FIXED)
    "DA": DA,

    # channel coefficient a = counter * DA, counter runs between these limits
    # mild control: nearest counters to a = 0.2 ... 0.6  (0.2 is not a multiple of 2^-7)
    "mild": (26, 77),         # a = 0.2031 ... 0.6016              (control channel)
    # primary candidate, NOT frozen until it passes the pilot tests (P-03)
    "primary": (40, 116),     # a = 0.3125 ... 0.90625

    "ebn0_pilot": [14.0, 16.0],   # dB, relative to transmitted symbol energy (APPROVED, P-01)

    "N_T": 30000,         # training length (symbols), static channel   (PROVISIONAL, checked in P1)
    "N_eval": 152000,     # evaluation length after N_T                 (PROVISIONAL)

    # PRBS training sequence: x^15 + x^14 + 1, period 2^15 - 1 = 32767
    "prbs_nbits": 15, "prbs_taps": (15, 14), "prbs_seed": 1,

    "pilot_seeds": list(range(1000, 1100)),   # used to choose parameters
    "final_seeds": list(range(2000, 2100)),   # used only after FREEZE-1
}


def sigma_from_ebn0(ebn0_db):
    """Noise standard deviation per real sample. x = +-1 so Eb = 1, N0 = 2*sigma^2."""
    return (1.0 / (2.0 * 10.0 ** (ebn0_db / 10.0))) ** 0.5
