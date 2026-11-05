# protocol.py -- PC side of the host_if.v command protocol (used by the simulation test and by the board script).
# Responsible member: Gautam Garg (review, verification, viva)
# Written with AI assistance (Claude, Anthropic), project decision D-06.
import struct

REPORT_LEN = 48


def config_frame(p, S, c_lo, c_hi, static, sigma_q, n_t, n_total, pay_seed, seeds):
    """'X' + 81 bytes. S = None or static=True gives a static channel (S is then sent as 1)."""
    static = bool(static) or S is None
    b = bytearray(b"X")
    b += struct.pack("<BHBBB", p, 1 if S is None else S, c_lo, c_hi, 1 if static else 0)
    b += sigma_q.to_bytes(3, "little")
    b += struct.pack("<III", n_t, n_total, pay_seed)
    assert len(seeds) == 12
    for s in seeds:
        b += int(s).to_bytes(5, "little")
    assert len(b) == 82
    return bytes(b)


def parse_report(r):
    """48-byte report -> dict; raises ValueError on a bad header or checksum."""
    if len(r) != REPORT_LEN or r[0] != 0xA5 or r[1] != 0x5A:
        raise ValueError("bad report header/length: %r" % bytes(r[:4]))
    body = r[2:47]
    x = 0
    for v in body:
        x ^= v
    if x != r[47]:
        raise ValueError("report checksum mismatch")
    status, sym_idx, n_eval, e1, e2, e3, sse2, sse3, stalls, updates = struct.unpack("<BIIIIIQQII", bytes(body))
    return dict(running=bool(status & 1), done=bool(status & 2), tracking=bool(status & 4), host=bool(status & 8),
                sym_idx=sym_idx, counters=[n_eval, e1, e2, e3, sse2, sse3, stalls, updates])


def parse_ident(r):
    if len(r) != 8 or bytes(r[:4]) != b"LMSF":
        raise ValueError("bad identification: %r" % bytes(r))
    return dict(B_MUL=r[4], B_ACC=r[5], RND=r[6], version=r[7])
