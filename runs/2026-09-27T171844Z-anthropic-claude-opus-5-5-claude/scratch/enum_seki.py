"""Find 'live' positions whose best result is seki via a unique move.
Usage: python3 enum_seki.py <wall> <outfile>"""
import itertools
import sys
import time
import gotools
from gotools import *
gotools.SECONDARY_MAXNODES = 1_000_000
import enumw


def main():
    wall, outfn = sys.argv[1], sys.argv[2]
    rows = enumw.WALLS[wall]
    b0, region, safe, target = diagram(rows)
    att, dfn = BLACK, WHITE
    solver = dfn
    interior = sorted(i for i in region if b0.b[i] == EMPTY)
    wallpts = sorted(i for i in region if b0.b[i] == dfn)
    out = open(outfn, 'w')
    t0 = time.time()
    seen = 0
    configs = []
    for nb_ in (1, 2, 3):
        for bset in itertools.combinations(interior, nb_):
            rest = [i for i in interior if i not in bset]
            for wopt in [None] + rest:
                configs.append((bset, wopt))
    for (bset, wopt) in configs:
        b = b0.copy()
        for i in bset:
            b.b[i] = att
        if wopt is not None:
            b.b[wopt] = dfn
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
        # quick filter: no clean life (config A) for any move
        gotools.FAST = True
        resA, ovA, _ = classify(prob, b, solver, solver, 'live', maxnodes=600_000)
        if ovA.get('A') == -2 or any(v == 'win' for v in resA.values()):
            continue
        gotools.FAST = False
        # seki check: config S only (non-strict, attacker wins kos)
        r, mv, st = prob.solve(b, solver, att, 0, maxnodes=1_000_000)
        if r == -2 or r in (2, 3, 4):
            continue
        sekis = sorted(m for m, v in mv.items() if v == 1 and m != 'pass')
        if len(sekis) != 1:
            continue
        # opponent first should kill (no seki for defender)
        r2, mv2, st2 = prob.solve(b, att, att, 0, maxnodes=1_000_000)
        if r2 != 1:
            continue
        seen += 1
        out.write('#%d wall=%s key=%s B=%s W=%s\n' % (seen, wall, sekis[0], ','.join(i2sgf(i) for i in bset),
                                                     i2sgf(wopt) if wopt is not None else '-'))
        out.write(b.show(0, 0, 10, 5, marks={sgf2i(sekis[0]): '*'}) + '\n')
        out.flush()
    out.write('done %d configs=%d %.0fs\n' % (seen, len(configs), time.time() - t0))
    out.close()


if __name__ == '__main__':
    main()
