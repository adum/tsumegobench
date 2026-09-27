"""Kill-focused enumeration on side walls: white group, black to kill.
Usage: python3 enum_kill.py <width> <height> <outfile> [mindepth]"""
import itertools
import sys
import time
import gotools
from gotools import *
gotools.FAST = True
import etree
import gentree
from mine5 import tree_stats, branch_count


def wall_rows(w, h):
    # white wall: columns x=2 and x=w+3 from y=0..h-1, row y=h from x=2..w+3; black safe outside
    W = w + 6
    rows = []
    for y in range(h + 2):
        r = ''
        for x in range(W):
            if y < h:
                if x in (1, w + 4):
                    r += 'B'
                elif x in (2, w + 3):
                    r += 'o'
                elif 3 <= x <= w + 2:
                    r += '.'
                else:
                    r += '-'
            elif y == h:
                if x in (1, w + 4):
                    r += 'B'
                elif 2 <= x <= w + 3:
                    r += 'o'
                else:
                    r += '-'
            else:
                if 1 <= x <= w + 4:
                    r += 'B'
                else:
                    r += '-'
        rows.append(r)
    return rows


def main():
    w, h, outfn = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    mind = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    rows = wall_rows(w, h)
    b0, region, safe, target = diagram(rows)
    interior = sorted(i for i in region if b0.b[i] == EMPTY)
    wallpts = sorted(i for i in region if b0.b[i] == WHITE)
    ends_first = [xy2i(2, 0), xy2i(w + 3, 0)]
    out = open(outfn, 'w')
    out.write('ROWS ' + '|'.join(rows) + '\n')
    t0 = time.time()
    seen = 0
    configs = []
    # perturbation types
    pert = [('none', None)]
    for g in wallpts:
        pert.append(('gap', g))
    for e in ends_first:
        pert.append(('hane', e))  # black replaces white end stone on first line
    for p1, p2 in itertools.combinations(pert, 2):
        pass
    for kind, pt in pert:
        for bset in [()] + [(i,) for i in interior]:
            for wopt in [None] + interior:
                if wopt is not None and wopt in bset:
                    continue
                configs.append((kind, pt, bset, wopt))
    for kind, pt, bset, wopt in configs:
        b = b0.copy()
        reg = set(region)
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
                    ok = False
                    break
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
        prob = Problem(b, reg, safe, tgt, BLACK)
        try:
            res, ov, st = classify(prob, b, BLACK, BLACK, 'kill', maxnodes=600_000)
        except Exception:
            continue
        if ov.get('A') == -2 or not res:
            continue
        wins = [m for m, v in res.items() if v == 'win']
        if len(wins) != 1 or wins[0] == 'pass':
            continue
        s2 = status(prob, b, WHITE, BLACK, 'kill')
        if s2 == 'win':
            continue
        etree._cache.clear()
        etree._scache.clear()
        etree.MAXNODES = 600_000
        try:
            frags = gentree.gen(prob, b, BLACK, 'kill', maxans=2)
            d, nodes, s = tree_stats(frags)
            if d < mind or nodes > 40:
                continue
            bc = branch_count(prob, b, BLACK, 'kill')
        except Exception:
            continue
        seen += 1
        out.write('#%d w=%d h=%d kind=%s pt=%s B=%s W=%s key=%s depth=%d nodes=%d branch=%d\n' % (
            seen, w, h, kind, i2sgf(pt) if pt is not None else '-', ','.join(i2sgf(i) for i in bset) or '-',
            i2sgf(wopt) if wopt is not None else '-', wins[0], d, nodes, bc))
        out.write(b.show(0, 0, w + 6, h + 2, marks={sgf2i(wins[0]): '*'}) + '\n')
        out.write('TREE ' + s + '\n')
        out.flush()
    out.write('done %d configs=%d %.0fs\n' % (seen, len(configs), time.time() - t0))
    out.close()


if __name__ == '__main__':
    main()
