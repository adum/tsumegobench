"""Targeted miner.
Usage: python3 mine5.py seed count objective(live|kill|any) mind maxd maxbranch sidefrac outfile [maxregion]
Reports positions with unique key, opp-first success, crisp auto tree within depth range."""
import random
import sys
import time
from gotools import *
from mine import build_corner, build_side, legal_setup, evaluate
import etree
import gentree


def tree_stats(frag_list):
    """Parse auto-tree fragments (SGF-ish) to compute depth and node count."""
    s = ''.join('(%s)' % f for f in frag_list)
    depth = 0
    cur = 0
    stack = []
    nodes = s.count(';')
    for ch in s:
        if ch == '(':
            stack.append(cur)
        elif ch == ')':
            cur = stack.pop()
        elif ch == ';':
            cur += 1
            depth = max(depth, cur)
    return depth, nodes, s


def branch_count(prob, board, solver, objective, depth=0, maxdepth=13):
    """Number of solver nodes with >=2 winning moves in the strong-threat tree."""
    res = etree.labels(prob, board, solver, solver, objective)
    if '*settled*' in res:
        return 0
    wins = [m for m in etree.winning(res) if m != 'pass']
    cnt = 1 if len(wins) >= 2 else 0
    if depth >= maxdepth:
        return cnt
    for m in wins:
        nb = etree.after(board, m, solver)
        ok, th = etree.threats(prob, nb, solver, objective)
        for om, w3, nb2, lab in th:
            if len([w for w in w3 if w != 'pass']) <= 2:
                cnt += branch_count(prob, nb2, solver, objective, depth + 2, maxdepth)
    return cnt


def main():
    seed, count, objective = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    mind, maxd, maxbranch = int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
    sidefrac = float(sys.argv[7])
    out = open(sys.argv[8], 'w')
    maxregion = int(sys.argv[9]) if len(sys.argv) > 9 else 16
    rng = random.Random(seed)
    found = 0
    t0 = time.time()
    for it in range(count):
        att = rng.choice([BLACK, WHITE])
        if objective == 'live':
            solver = opp(att)
        elif objective == 'kill':
            solver = att
        else:
            solver = rng.choice([att, opp(att)])
        if rng.random() < sidefrac:
            b, region, safe, target = build_side(rng, att, {'wmin': 4, 'wmax': 8, 'maxh': 2, 'maxper': 3})
        else:
            params = {'maxx': rng.choice([4, 5, 6]), 'maxy': rng.choice([3, 4, 5]), 'minper': 1, 'maxper': 3}
            b, region, safe, target = build_corner(rng, att, params)
        if not legal_setup(b) or len(region) > maxregion or len(region) < 4:
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
        etree._cache.clear()
        etree._scache.clear()
        try:
            frags = gentree.gen(prob, b, solver, obj, maxans=2)
            d, nodes, s = tree_stats(frags)
            if d < mind or d > maxd:
                continue
            bc = branch_count(prob, b, solver, obj)
            if bc > maxbranch:
                continue
        except Exception:
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
