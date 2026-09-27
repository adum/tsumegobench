"""Generate SGF subtree strings from the essential tree."""
import sys
from gotools import *
import etree


def gen(prob, board, solver, objective, depth=0, maxdepth=13, maxans=2, only=None):
    """Solver to move. Returns SGF fragment for all winning moves (each as a variation)."""
    res = etree.labels(prob, board, solver, solver, objective)
    wins = [m for m in etree.winning(res) if m != 'pass']
    if only is not None:
        wins = [m for m in wins if m in only]
    frags = []
    for m in wins:
        nb = etree.after(board, m, solver)
        ok, th = etree.threats(prob, nb, solver, objective)
        mv = '%s[%s]' % (CNAME[solver], m)
        strong = [(om, w3, nb2) for om, w3, nb2, lab in th if len([w for w in w3 if w != 'pass']) <= maxans]
        if not strong or depth + 1 >= maxdepth:
            frags.append(';%sC[RIGHT]' % mv)
            continue
        subs = []
        for om, w3, nb2 in strong:
            inner = gen(prob, nb2, solver, objective, depth + 2, maxdepth, maxans)
            o = CNAME[opp(solver)]
            if len(inner) == 1:
                subs.append(';%s[%s]%s' % (o, om, inner[0]))
            else:
                subs.append(';%s[%s]%s' % (o, om, ''.join('(%s)' % f for f in inner)))
        if len(subs) == 1:
            frags.append(';%s%s' % (mv, subs[0]))
        else:
            frags.append(';%s%s' % (mv, ''.join('(%s)' % s for s in subs)))
    return frags


if __name__ == '__main__':
    import designs
    from design import load
    name = sys.argv[1]
    seq = [m for m in (sys.argv[2].split(',') if len(sys.argv) > 2 else []) if m]
    maxans = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    d, prob = load(name)
    b = prob.board.copy()
    c = d['first']
    for m in seq:
        b = etree.after(b, m, c)
        c = opp(c)
    fr = gen(prob, b, d['solver'], d['objective'], maxans=maxans)
    print(''.join('(%s)' % f for f in fr))
