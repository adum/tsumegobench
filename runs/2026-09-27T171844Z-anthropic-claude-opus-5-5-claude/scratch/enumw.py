"""Systematic enumeration of inside-stone placements for fixed natural walls.
Usage: python3 enum.py <wallname> <objective live|kill> <outfile> [mindepth]"""
import itertools
import sys
import time
import gotools
from gotools import *
gotools.FAST = True
import etree
import gentree
from mine5 import tree_stats, branch_count

WALLS = {
    # defender white corner group, attacker black safe
    'WA': ["....oB",
           "....oB",
           "...ooB",
           "ooooBB",
           "BBBBB-"],
    'WB': ["...oB",
           "...oB",
           "...oB",
           "ooooB",
           "BBBBB"],
    'WC': ["-Bo.....oB-",
           "-Bo.....oB-",
           "-BoooooooB-",
           "-BBBBBBBBB-"],
    'WD': [".....oB",
           ".....oB",
           "..oooBB",
           "ooo.BB-",
           "BBBBB--"],
    'WE': ["-Bo......oB",
           "-Bo......oB",
           "-BooooooooB",
           "-BBBBBBBBBB"],
    'WG': ["....oB",
           "....oB",
           "oooooB",
           "BBBBBB"],
    'WH': [".....oB",
           ".....oB",
           "ooooooB",
           "BBBBBBB"],
    'WI': ["-Bo......oB-",
           "-Bo......oB-",
           "-BooooooooB-",
           "-BBBBBBBBBB-"],
    'WJ': ["...oB",
           "...oB",
           "..ooB",
           "oooBB",
           "BBBB-"],
    'WK': ["....oB",
           "...ooB",
           ".oooBB",
           "ooBB--",
           "BB----"],
    'WL': ["-B.....oB",
           "-B.ooooob".replace('b', 'B'),
           "-BooBBBBB",
           "-BBB-----"],
    'WM': ["-B......oB",
           "-B...oooob".replace('b', 'B'),
           "-BoooBBBBB",
           "-BBBBB----"],
    'WF': ["....oB-",
           "....oB-",
           "....oB-",
           "..oooB-",
           "ooo.BB-",
           "BBBBB--"],
}


def main():
    wall, objective, outfn = sys.argv[1], sys.argv[2], sys.argv[3]
    mind = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    rows = WALLS[wall]
    b0, region, safe, target = diagram(rows)
    # colors: defender white, attacker black (we can color-swap later)
    att = BLACK
    dfn = WHITE
    solver = att if objective == 'kill' else dfn
    interior = sorted(i for i in region if b0.b[i] == EMPTY)
    wallpts = sorted(i for i in region if b0.b[i] == dfn)
    out = open(outfn, 'w')
    t0 = time.time()
    seen = 0
    configs = []
    for nb_ in (1, 2):
        for bset in itertools.combinations(interior, nb_):
            rest = [i for i in interior if i not in bset]
            for wopt in [None] + rest:
                configs.append((bset, wopt, None))
            for gap in wallpts:
                configs.append((bset, None, gap))
    for (bset, wopt, gap) in configs:
        b = b0.copy()
        for i in bset:
            b.b[i] = att
        if wopt is not None:
            b.b[wopt] = dfn
        if gap is not None:
            b.b[gap] = EMPTY
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
            if b.b[i] == dfn:
                st, lb = b.chain(i)
                if len(st) > len(tgt):
                    tgt = st
        if len(tgt) < 4:
            continue
        prob = Problem(b, region, safe, tgt, att)
        try:
            res, overall, stats = classify(prob, b, solver, solver, objective, maxnodes=800_000)
        except Exception:
            continue
        if overall.get('A') == -2 or not res:
            continue
        wins = [m for m, v in res.items() if v == 'win']
        if len(wins) != 1 or wins[0] == 'pass':
            continue
        st = status(prob, b, opp(solver), solver, objective)
        if st != 'lose':
            continue
        etree._cache.clear()
        etree._scache.clear()
        etree.MAXNODES = 800_000
        try:
            frags = gentree.gen(prob, b, solver, objective, maxans=2)
            d, nodes, s = tree_stats(frags)
            if d < mind or nodes > 40:
                continue
            bc = branch_count(prob, b, solver, objective)
        except Exception:
            continue
        seen += 1
        key = wins[0]
        out.write('#%d wall=%s obj=%s key=%s depth=%d nodes=%d branch=%d B=%s W=%s gap=%s\n' % (
            seen, wall, objective, key, d, nodes, bc, ','.join(i2sgf(i) for i in bset),
            i2sgf(wopt) if wopt is not None else '-', i2sgf(gap) if gap is not None else '-'))
        out.write(b.show(0, 0, 10, 5, marks={sgf2i(key): '*'}) + '\n')
        out.write('TREE ' + s + '\n')
        out.flush()
    out.write('done %d configs=%d %.0fs\n' % (seen, len(configs), time.time() - t0))
    out.close()


if __name__ == '__main__':
    main()
