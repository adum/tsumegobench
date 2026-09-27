"""Miner with crisp metric. Usage: python3 mine4.py seed count mindepth maxnodes outfile sidefrac"""
import random, sys, time
from gotools import *
from mine import build_corner, build_side, legal_setup, evaluate
import etree, crisp


def main():
    seed, count, mind, maxn = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    out = open(sys.argv[5], 'w')
    sidefrac = float(sys.argv[6])
    rng = random.Random(seed)
    found = 0
    t0 = time.time()
    for it in range(count):
        att = rng.choice([BLACK, WHITE])
        solver = rng.choice([att, opp(att)])
        if rng.random() < sidefrac:
            b, region, safe, target = build_side(rng, att, {'wmin': 4, 'wmax': 8, 'maxh': 2, 'maxper': 3})
        else:
            params = {'maxx': rng.choice([4, 5, 6]), 'maxy': rng.choice([3, 4, 5]), 'minper': 1, 'maxper': 3}
            b, region, safe, target = build_corner(rng, att, params)
        if not legal_setup(b) or len(region) > 16 or len(region) < 5:
            continue
        try:
            r = evaluate(b, region, safe, target, att, solver, maxnodes=1_000_000)
        except Exception:
            continue
        if r is None:
            continue
        prob, res, key, st = r
        objective = 'kill' if solver == att else 'live'
        etree._cache.clear(); etree._scache.clear()
        try:
            D, S, MW = crisp.crisp(prob, b, solver, objective)
        except Exception:
            continue
        if D < mind or S > maxn or MW > 2:
            continue
        found += 1
        others = ' '.join('%s:%s' % (m, v) for m, v in sorted(res.items()) if v not in ('lose', 'win'))
        out.write('#%d seed=%d it=%d solver=%s obj=%s key=%s depth=%d nodes=%d opp-first=%s others=[%s] region=%d\n' % (
            found, seed, it, CNAME[solver], objective, key, D, S, st, others, len(region)))
        out.write(b.show(0, 0, 14, 6, marks={sgf2i(key): '*'}) + '\n')
        out.write('REGION ' + ','.join(i2sgf(i) for i in sorted(region)) + '\n')
        out.write('SAFE ' + ','.join(i2sgf(i) for i in sorted(safe)) + '\n')
        out.write('TARGET ' + ','.join(i2sgf(i) for i in sorted(prob.target)) + '\n')
        out.flush()
    out.write('done %d %.0fs\n' % (found, time.time() - t0))
    out.close()

main()
