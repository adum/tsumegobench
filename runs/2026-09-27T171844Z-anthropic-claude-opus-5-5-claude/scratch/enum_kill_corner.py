"""Kill enumeration on corner walls without inside attacker stones (0-1 black inside), with perturbations.
Usage: python3 enum_kill_corner.py <wall> <outfile> [mindepth]"""
import itertools, sys, time
import gotools
from gotools import *
gotools.FAST = True
import etree, gentree
from mine5 import tree_stats, branch_count
import enumw


def main():
    wall, outfn = sys.argv[1], sys.argv[2]
    mind = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    rows = enumw.WALLS[wall]
    b0, region, safe, target = diagram(rows)
    interior = sorted(i for i in region if b0.b[i] == EMPTY)
    wallpts = sorted(i for i in region if b0.b[i] == WHITE)
    # first-line wall end points (on edges)
    ends = [i for i in wallpts if (i % N == 0 or i // N == 0)]
    out = open(outfn, 'w')
    t0 = time.time(); seen = 0
    pert = [('none', None)] + [('gap', g) for g in wallpts] + [('hane', e) for e in ends]
    configs = []
    for kind, pt in pert:
        for bset in [()] + [(i,) for i in interior]:
            for wopt in [None] + interior:
                if wopt is not None and wopt in bset:
                    continue
                configs.append((kind, pt, bset, wopt))
    for kind, pt, bset, wopt in configs:
        b = b0.copy()
        if kind == 'gap':
            b.b[pt] = EMPTY
        elif kind == 'hane':
            b.b[pt] = BLACK
        for i in bset:
            b.b[i] = BLACK
        if wopt is not None:
            b.b[wopt] = WHITE
        ok = True
        for i in range(N * N):
            if b.b[i]:
                st, lb = b.chain(i)
                if not lb:
                    ok = False; break
        if not ok:
            continue
        tgt = set()
        for i in wallpts:
            if b.b[i] == WHITE:
                st, lb = b.chain(i)
                if len(st) > len(tgt):
                    tgt = st
        if len(tgt) < 5:
            continue
        prob = Problem(b, region, safe, tgt, BLACK)
        try:
            res, ov, st = classify(prob, b, BLACK, BLACK, 'kill', maxnodes=600_000)
        except Exception:
            continue
        if ov.get('A') == -2 or not res:
            continue
        wins = [m for m, v in res.items() if v == 'win']
        if len(wins) != 1 or wins[0] == 'pass':
            continue
        if status(prob, b, WHITE, BLACK, 'kill') == 'win':
            continue
        etree._cache.clear(); etree._scache.clear(); etree.MAXNODES = 600_000
        try:
            frags = gentree.gen(prob, b, BLACK, 'kill', maxans=2)
            d, nodes, s = tree_stats(frags)
            if d < mind or nodes > 40:
                continue
            bc = branch_count(prob, b, BLACK, 'kill')
        except Exception:
            continue
        seen += 1
        out.write('#%d wall=%s kind=%s pt=%s B=%s W=%s key=%s depth=%d nodes=%d branch=%d\n' % (
            seen, wall, kind, i2sgf(pt) if pt is not None else '-', ','.join(i2sgf(i) for i in bset) or '-',
            i2sgf(wopt) if wopt is not None else '-', wins[0], d, nodes, bc))
        out.write(b.show(0, 0, 8, 6, marks={sgf2i(wins[0]): '*'}) + '\n')
        out.write('TREE ' + s + '\n')
        out.flush()
    out.write('done %d configs=%d %.0fs\n' % (seen, len(configs), time.time() - t0))
    out.close()


if __name__ == '__main__':
    main()
