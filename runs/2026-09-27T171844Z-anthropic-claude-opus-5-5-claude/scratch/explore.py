"""Explore: apply a move sequence and print per-move results for side to move."""
from gotools import *


def apply_seq(board, seq, first):
    b = board.copy()
    c = first
    for m in seq:
        b.play(sgf2i(m), c)
        c = opp(c)
    return b, c


def explore(prob, seq, first, objective, solver_color, box=None, maxnodes=0):
    b, tomove = apply_seq(prob.board, seq, first)
    if box:
        print(b.show(*box))
    print('seq:', ' '.join(seq), ' to move:', CNAME[tomove], ' ko:', i2sgf(b.ko) if b.ko is not None else None)
    res, overall, stats = classify(prob, b, tomove, solver_color, objective, maxnodes=maxnodes)
    groups = {}
    for m, v in res.items():
        groups.setdefault(v, []).append(m)
    for k in sorted(groups):
        print('  %-5s %s' % (k, ' '.join(sorted(groups[k]))))
    print('  stats', stats)
    return res
