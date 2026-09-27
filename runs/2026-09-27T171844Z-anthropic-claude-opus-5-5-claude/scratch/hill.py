"""Hill-climb around a base design to find deep, crisp problems.
Usage: python3 hill.py <design> <iterations> <seed> <outfile> [mindepth]"""
import random
import sys
import time
from gotools import *
import designs
import etree
import gentree
from mine5 import tree_stats, branch_count


def load_design(name):
    d = designs.D[name]
    b, region, safe, target = diagram(d['rows'])
    if d.get('target'):
        target = {sgf2i(s) for s in d['target']}
    return d, b, region, safe, target


def largest_chain(b, pts, color):
    best = set()
    for i in pts:
        if b.b[i] == color:
            st, lb = b.chain(i)
            if len(st) > len(best):
                best = st
    return best


def legal_setup(b):
    for i in range(N * N):
        if b.b[i]:
            st, lb = b.chain(i)
            if not lb:
                return False
    return True


def evaluate(b, region, safe, target_pts, att, solver, objective):
    dfn = opp(att)
    tgt = largest_chain(b, target_pts, dfn)
    if len(tgt) < 3:
        return None
    prob = Problem(b, region, safe, tgt, att)
    res, overall, stats = classify(prob, b, solver, solver, objective, maxnodes=1_500_000)
    if any(v == -2 for v in overall.values()) or not res:
        return None
    wins = sorted(m for m, v in res.items() if v == 'win')
    if len(wins) != 1 or wins[0] == 'pass':
        return None
    st = status(prob, b, opp(solver), solver, objective)
    if st != 'lose':
        return None
    etree._cache.clear()
    etree._scache.clear()
    try:
        etree.MAXNODES = 1_500_000
        frags = gentree.gen(prob, b, solver, objective, maxans=2)
        d, nodes, s = tree_stats(frags)
        bc = branch_count(prob, b, solver, objective)
    except Exception:
        return None
    kos = sum(1 for v in res.values() if v in ('ko', 'seki'))
    return dict(key=wins[0], depth=d, nodes=nodes, branch=bc, tree=s, res=res, tgt=tgt, kos=kos)


def score(ev):
    return ev['depth'] * 10 - ev['nodes'] * 0.6 - ev['branch'] * 6


def main():
    name, iters, seed, outfn = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    mindepth = int(sys.argv[5]) if len(sys.argv) > 5 else 5
    rng = random.Random(seed)
    d, b0, region0, safe0, target0 = load_design(name)
    att, solver, objective = d['att'], d['solver'], d['objective']
    dfn = opp(att)
    mutable = sorted(region0 | {i for i in range(N * N) if b0.b[i] and i not in safe0})
    out = open(outfn, 'w')
    cur_b, cur_region = b0.copy(), set(region0)
    cur_ev = evaluate(cur_b, cur_region, safe0, target0 | {i for i in range(361) if b0.b[i] == dfn and i not in safe0}, att, solver, objective)
    cur_score = score(cur_ev) if cur_ev else -1e9
    best_seen = set()
    t0 = time.time()
    for it in range(iters):
        nb = cur_b.copy()
        nreg = set(cur_region)
        k = rng.choice([1, 1, 1, 2])
        for _ in range(k):
            p = rng.choice(mutable)
            nb.b[p] = rng.choice([v for v in (EMPTY, BLACK, WHITE) if v != nb.b[p]])
            nreg.add(p)
        if not legal_setup(nb):
            continue
        tpts = {i for i in mutable if nb.b[i] == dfn}
        ev = evaluate(nb, nreg, safe0, tpts, att, solver, objective)
        if ev is None:
            if cur_ev is None or rng.random() < 0.05:
                # random walk while no valid position yet (or occasional escape)
                cur_b, cur_region = nb, nreg
                cur_ev, cur_score = None, -1e9
            continue
        sc = score(ev)
        accept = sc >= cur_score or rng.random() < 0.15
        if accept:
            cur_b, cur_region, cur_ev, cur_score = nb, nreg, ev, sc
        key = tuple(nb.b)
        if ev['depth'] >= mindepth and key not in best_seen and ev['branch'] <= 2:
            best_seen.add(key)
            out.write('#%d it=%d solver=%s obj=%s key=%s depth=%d nodes=%d branch=%d kos=%d score=%.1f\n' % (
                len(best_seen), it, CNAME[solver], objective, ev['key'], ev['depth'], ev['nodes'], ev['branch'], ev['kos'], sc))
            out.write(nb.show(0, 0, 14, 6, marks={sgf2i(ev['key']): '*'}) + '\n')
            out.write('REGION ' + ','.join(i2sgf(i) for i in sorted(nreg)) + '\n')
            out.write('SAFE ' + ','.join(i2sgf(i) for i in sorted(safe0)) + '\n')
            out.write('TARGET ' + ','.join(i2sgf(i) for i in sorted(ev['tgt'])) + '\n')
            out.write('TREE ' + ev['tree'] + '\n')
            out.flush()
    out.write('done %.0fs\n' % (time.time() - t0))
    out.close()


if __name__ == '__main__':
    main()
