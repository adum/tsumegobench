"""Trace principal line from a position until a ko capture appears (or N moves)."""
import sys
from design import load
import etree
from gotools import *

RANK = {'win': 3, 'seki': 2, 'ko': 1, 'lose': 0, 'lose?': 0}


def trace(prob, board, tomove, solver, objective, maxmoves=8, prefer=None):
    line = []
    b = board.copy()
    c = tomove
    for _ in range(maxmoves):
        res = etree.labels(prob, b, c, solver, objective)
        if '*settled*' in res:
            break
        cands = [(m, v) for m, v in res.items() if m != 'pass']
        if not cands:
            break
        if c == solver:
            best = max(RANK.get(v, 0) for m, v in cands)
        else:
            best = min(RANK.get(v, 0) for m, v in cands)
        opts = sorted(m for m, v in cands if RANK.get(v, 0) == best)
        m = opts[0]
        if prefer:
            for p in prefer:
                if p in opts:
                    m = p
                    break
        try:
            caps = b.play(sgf2i(m), c)
        except IllegalMove:
            break
        line.append((CNAME[c], m, [k for k, v in cands if RANK.get(v, 0) == best], len(caps), b.ko is not None))
        if b.ko is not None:
            break
        c = opp(c)
    return line


if __name__ == '__main__':
    d, prob = load(sys.argv[1])
    seq = sys.argv[2].split(',')
    b = prob.board.copy(); c = d['first']
    for m in seq:
        b.play(sgf2i(m), c); c = opp(c)
    for step in trace(prob, b, c, d['solver'], d['objective']):
        print(step)
