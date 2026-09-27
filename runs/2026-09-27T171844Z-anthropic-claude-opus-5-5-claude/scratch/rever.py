"""Re-verify mined candidates with target = largest defender chain; print classification + auto tree."""
import sys
from gotools import *
import minedload, etree, gentree
from mine5 import tree_stats


def fix_target(c):
    b = c['board']
    dfn = opp(c['att'])
    best = set()
    for i in c['target']:
        if b.b[i] == dfn:
            st, lb = b.chain(i)
            if len(st) > len(best):
                best = st
    c['target'] = best
    return c


if __name__ == '__main__':
    for spec in sys.argv[1:]:
        fn, idx = spec.split(':')
        cs = minedload.parse_file(fn)
        c = [c for c in cs if c['hdr'].startswith('#%s ' % idx)][0]
        c = fix_target(c)
        prob = minedload.to_problem(c)
        b = prob.board
        print('=====', spec, c['hdr'])
        xs = [i % 19 for i in range(361) if b.b[i]]
        print(b.show(0, 0, max(xs) + 1, 4))
        res, overall, stats = classify(prob, b, c['solver'], c['solver'], c['objective'])
        print('labels:', ' '.join('%s:%s' % kv for kv in sorted(res.items()) if kv[1] != 'lose'))
        st = status(prob, b, opp(c['solver']), c['solver'], c['objective'])
        print('opp-first:', st)
        etree._cache.clear(); etree._scache.clear()
        frags = gentree.gen(prob, b, c['solver'], c['objective'], maxans=2)
        d, n, s = tree_stats(frags)
        print('auto tree depth=%d nodes=%d' % (d, n))
        print(s)
