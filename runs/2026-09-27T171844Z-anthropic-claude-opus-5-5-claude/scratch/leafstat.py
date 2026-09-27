import sys
import gotools
from gotools import *
from design import load
d, prob = load(sys.argv[1])
tree = sys.argv[2]
root = parse_sgf('(;SZ[19]' + tree + ')')
def rec(node, b, path):
    for ch in node.children:
        c, m = ch.move()
        nb = b.copy(); nb.play(sgf2i(m), c)
        p = path + [CNAME[c] + m]
        if not ch.children:
            st = status(prob, nb, opp(c), d['solver'], 'live')
            print(' '.join(p), '->', st, ch.comment())
        rec(ch, nb, p)
rec(root, prob.board.copy(), [])
