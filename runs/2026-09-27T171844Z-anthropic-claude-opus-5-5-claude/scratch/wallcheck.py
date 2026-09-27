from gotools import *
import final
for n in sorted(final.P):
    sgf, spec = final.make(n)
    root = parse_sgf(sgf)
    b = board_from_sgf_root(root)
    att = spec.attacker
    weak = []
    seen = set()
    for i in spec.safe:
        if b.b[i] and i not in seen:
            st, lb = b.chain(i)
            seen |= st
            if len(lb) <= 3:
                weak.append((sorted(i2sgf(s) for s in st), sorted(i2sgf(l) for l in lb)))
    print(n, final.P[n]['design'], 'weak safe chains:', weak)
