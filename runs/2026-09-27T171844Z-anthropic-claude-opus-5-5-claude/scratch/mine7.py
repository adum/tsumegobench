"""Fast deep miner (unconditional-only analysis). Usage: seed count mind maxd sidefrac outfile maxregion"""
import random, sys, time
import gotools
from gotools import *
gotools.FAST = True
from mine import build_corner, build_side, legal_setup
import etree, gentree
from mine5 import tree_stats, branch_count
from mine6 import sacrifice_replay


def evaluate_fast(b, region, safe, target, att, solver, maxnodes=1_000_000):
    dfn = opp(att)
    target = {i for i in target if b.b[i] == dfn}
    best = set()
    for i in target:
        st, lb = b.chain(i)
        if len(st) > len(best):
            best = st
    if len(best) < 4:
        return None
    prob = Problem(b, region, safe, best, att)
    objective = 'kill' if solver == att else 'live'
    res, overall, stats = classify(prob, b, solver, solver, objective, maxnodes=maxnodes)
    if overall.get('A') == -2 or not res:
        return None
    wins = sorted(m for m, v in res.items() if v == 'win')
    if len(wins) != 1 or wins[0] == 'pass':
        return None
    st = status(prob, b, opp(solver), solver, objective)
    if st != 'lose':
        return None
    return prob, res, wins[0]


def main():
    seed, count, mind, maxd = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    sidefrac = float(sys.argv[5]); out = open(sys.argv[6], 'w'); maxregion = int(sys.argv[7])
    rng = random.Random(seed)
    found = 0; t0 = time.time()
    for it in range(count):
        att = rng.choice([BLACK, WHITE])
        solver = rng.choice([att, opp(att)])
        if rng.random() < sidefrac:
            b, region, safe, target = build_side(rng, att, {'wmin': 5, 'wmax': 9, 'maxh': 2, 'maxper': 3})
        else:
            params = {'maxx': rng.choice([4, 5, 6]), 'maxy': rng.choice([3, 4, 5]), 'minper': 1, 'maxper': 3}
            b, region, safe, target = build_corner(rng, att, params)
        if not legal_setup(b) or len(region) > maxregion or len(region) < 6:
            continue
        try:
            r = evaluate_fast(b, region, safe, target, att, solver)
        except Exception:
            continue
        if r is None:
            continue
        prob, res, key = r
        obj = 'kill' if solver == att else 'live'
        etree._cache.clear(); etree._scache.clear()
        etree.MAXNODES = 1_000_000
        try:
            frags = gentree.gen(prob, b, solver, obj, maxans=2)
            d, nodes, s = tree_stats(frags)
            if d < mind or d > maxd or nodes > 40:
                continue
            bc = branch_count(prob, b, solver, obj)
            if bc > 2:
                continue
            sac = sacrifice_replay(prob, b, s, solver)
        except Exception:
            continue
        ki = sgf2i(key)
        firstline = (ki // N == 0) or (ki % N == 0)
        adj_solver = any(b.b[q] == solver for q in neighbors(ki))
        found += 1
        out.write('#%d seed=%d it=%d solver=%s obj=%s key=%s depth=%d nodes=%d branch=%d sac=%d first=%d placement=%d region=%d\n' % (
            found, seed, it, CNAME[solver], obj, key, d, nodes, bc, sac, firstline, 0 if adj_solver else 1, len(region)))
        out.write(b.show(0, 0, 14, 6, marks={ki: '*'}) + '\n')
        out.write('REGION ' + ','.join(i2sgf(i) for i in sorted(region)) + '\n')
        out.write('SAFE ' + ','.join(i2sgf(i) for i in sorted(safe)) + '\n')
        out.write('TARGET ' + ','.join(i2sgf(i) for i in sorted(prob.target)) + '\n')
        out.write('TREE ' + s + '\n')
        out.flush()
    out.write('done %d %.0fs\n' % (found, time.time() - t0))
    out.close()

main()
