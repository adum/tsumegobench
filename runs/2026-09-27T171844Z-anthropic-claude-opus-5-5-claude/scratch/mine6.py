"""Miner for sacrifice-replay tactics. Usage: python3 mine6.py seed count objective mind maxd sidefrac outfile maxregion"""
import random, sys, time, re
from gotools import *
from mine import build_corner, build_side, legal_setup, evaluate
import etree, gentree
from mine5 import tree_stats, branch_count


def sacrifice_replay(prob, board, tree_s, solver):
    """Walk every RIGHT line; flag if solver stones (>=2) were captured and solver later played on a captured point."""
    root = parse_sgf('(;SZ[19]' + tree_s[1:] if False else '(;SZ[19]' + tree_s + ')')
    found = [False]

    def rec(node, b, captured_pts):
        for ch in node.children:
            mv = ch.move()
            c, m = mv
            nb = b.copy()
            try:
                caps = nb.play(sgf2i(m), c)
            except IllegalMove:
                continue
            cp = set(captured_pts)
            if c != solver and len(caps) >= 2:
                cp |= set(caps)
            if c == solver and sgf2i(m) in captured_pts:
                found[0] = True
            rec(ch, nb, cp)
    rec(root, board, set())
    return found[0]


def main():
    seed, count, objective = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    mind, maxd = int(sys.argv[4]), int(sys.argv[5])
    sidefrac = float(sys.argv[6])
    out = open(sys.argv[7], 'w')
    maxregion = int(sys.argv[8])
    rng = random.Random(seed)
    found = 0
    t0 = time.time()
    for it in range(count):
        att = rng.choice([BLACK, WHITE])
        solver = opp(att) if objective == 'live' else (att if objective == 'kill' else rng.choice([att, opp(att)]))
        if rng.random() < sidefrac:
            b, region, safe, target = build_side(rng, att, {'wmin': 4, 'wmax': 8, 'maxh': 2, 'maxper': 4})
        else:
            params = {'maxx': rng.choice([4, 5, 6]), 'maxy': rng.choice([3, 4, 5]), 'minper': 1, 'maxper': 4}
            b, region, safe, target = build_corner(rng, att, params)
        if not legal_setup(b) or len(region) > maxregion or len(region) < 5:
            continue
        try:
            r = evaluate(b, region, safe, target, att, solver, maxnodes=1_000_000)
        except Exception:
            continue
        if r is None:
            continue
        prob, res, key, st = r
        if st != 'lose':
            continue
        obj = 'kill' if solver == att else 'live'
        etree._cache.clear(); etree._scache.clear()
        try:
            frags = gentree.gen(prob, b, solver, obj, maxans=2)
            d, nodes, s = tree_stats(frags)
            if d < mind or d > maxd or nodes > 45:
                continue
            if not sacrifice_replay(prob, b, s, solver):
                continue
            bc = branch_count(prob, b, solver, obj)
        except Exception as e:
            continue
        found += 1
        others = ' '.join('%s:%s' % (m, v) for m, v in sorted(res.items()) if v not in ('lose', 'win'))
        out.write('#%d seed=%d it=%d solver=%s obj=%s key=%s depth=%d nodes=%d branch=%d others=[%s] region=%d\n' % (
            found, seed, it, CNAME[solver], obj, key, d, nodes, bc, others, len(region)))
        out.write(b.show(0, 0, 14, 6, marks={sgf2i(key): '*'}) + '\n')
        out.write('REGION ' + ','.join(i2sgf(i) for i in sorted(region)) + '\n')
        out.write('SAFE ' + ','.join(i2sgf(i) for i in sorted(safe)) + '\n')
        out.write('TARGET ' + ','.join(i2sgf(i) for i in sorted(prob.target)) + '\n')
        out.write('TREE ' + s + '\n')
        out.flush()
    out.write('done %d %.0fs\n' % (found, time.time() - t0))
    out.close()

if __name__ == '__main__':
    main()
