"""Build SGF from design (diagram + tree string in design coords) with a symmetry transform."""
import re
import sys
from gotools import *
from validate import Spec, check
import designs


SHIFT = (0, 0)


def tfi(i, t):
    j = transform_i(i, t)
    x, y = j % N + SHIFT[0], j // N + SHIFT[1]
    assert 0 <= x < N and 0 <= y < N
    return y * N + x


def tf(s, t):
    return i2sgf(tfi(sgf2i(s), t))


def build(name, tree, t=0, extra_black=(), extra_white=(), shift=(0, 0), swap=False):
    global SHIFT
    SHIFT = shift
    d = designs.D[name]
    b, region, safe, target = diagram(d['rows'])
    if d.get('target'):
        target = {sgf2i(s) for s in d['target']}
    if swap:
        for i in range(361):
            if b.b[i]:
                b.b[i] = 3 - b.b[i]
        tree = re.sub(r'([BW])\[', lambda m: ('W' if m.group(1) == 'B' else 'B') + '[', tree)
    blacks = sorted(i2sgf(tfi(i, t)) for i in range(361) if b.b[i] == BLACK)
    whites = sorted(i2sgf(tfi(i, t)) for i in range(361) if b.b[i] == WHITE)
    blacks += [tf(s, t) for s in extra_black]
    whites += [tf(s, t) for s in extra_white]
    tree_t = re.sub(r'([BW])\[([a-s]{2})\]', lambda m: '%s[%s]' % (m.group(1), tf(m.group(2), t)), tree)
    root = '(;GM[1]FF[4]CA[UTF-8]SZ[19]AB%sAW%s%s)' % (''.join('[%s]' % s for s in sorted(blacks)),
                                                    ''.join('[%s]' % s for s in sorted(whites)), tree_t)
    att, solver = d['att'], d['solver']
    if swap:
        att, solver = 3 - att, 3 - solver
    spec = Spec({tfi(i, t) for i in region}, {tfi(i, t) for i in safe},
                {tfi(i, t) for i in target}, att, d['objective'], solver)
    return root, spec


if __name__ == '__main__':
    pass
