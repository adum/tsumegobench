"""Miner with essential-depth metric. Usage: python3 mine2.py seed count mindepth outfile"""
import random, sys, time
from gotools import *
from mine import build_corner, build_side, legal_setup, evaluate
import etree


def edepth(prob, board, solver, objective, depth=0, maxdepth=14):
    res = etree.labels(prob, board, solver, solver, objective)
    if '*settled*' in res:
        return 0
    wins = etree.winning(res)
    if not wins or len(wins) > 2:
        return 0
    best = 0
    for m in wins:
        if m == 'pass':
            continue
        nb = etree.after(board, m, solver)
        ok, th = etree.threats(prob, nb, solver, objective)
        d = 1
        if depth + 2 <= maxdepth:
            for om, w3, nb2, lab in th[:6]:
                d = max(d, 2 + edepth(prob, nb2, solver, objective, depth + 2, maxdepth))
        best = max(best, d)
    return best


def main():
    seed, count, mind = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    out = open(sys.argv[4], 'w')
    rng = random.Random(seed)
    found = 0
    t0 = time.time()
    for it in range(count):
        att = rng.choice([BLACK, WHITE])
        solver = rng.choice([att, opp(att)])
        params = {'maxx': rng.choice([5, 6, 7]), 'maxy': rng.choice([4, 5, 6]), 'minper': 1, 'maxper': 4}
        if rng.random() < SIDEFRAC:
            b, region, safe, target = build_side(rng, att, {})
        else:
            b, region, safe, target = build_corner(rng, att, params)
        if not legal_setup(b) or len(region) > 18 or len(region) < 5:
            continue
        try:
            r = evaluate(b, region, safe, target, att, solver, maxnodes=2_000_000)
        except Exception:
            continue
        if r is None:
            continue
        prob, res, key, st = r
        objective = 'kill' if solver == att else 'live'
        etree._cache.clear(); etree._scache.clear()
        try:
            d = edepth(prob, b, solver, objective)
        except Exception:
            continue
        if d < mind:
            continue
        found += 1
        others = ' '.join('%s:%s' % (m, v) for m, v in sorted(res.items()) if v not in ('lose', 'win'))
        out.write('#%d seed=%d it=%d solver=%s obj=%s key=%s depth=%d opp-first=%s others=[%s] region=%d\n' % (
            found, seed, it, CNAME[solver], objective, key, d, st, others, len(region)))
        out.write(b.show(0, 0, 14, 6, marks={sgf2i(key): '*'}) + '\n')
        out.write('REGION ' + ','.join(i2sgf(i) for i in sorted(region)) + '\n')
        out.write('SAFE ' + ','.join(i2sgf(i) for i in sorted(safe)) + '\n')
        out.write('TARGET ' + ','.join(i2sgf(i) for i in sorted(prob.target)) + '\n')
        out.flush()
    out.write('done %d %.0fs\n' % (found, time.time() - t0))
    out.close()

SIDEFRAC = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
main()
