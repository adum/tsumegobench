"""Mutation search around a base design.
Usage: python3 mutate.py <design> <mutable points comma list> [maxmut]
Each mutable point is tried as empty(region)/defender stone/attacker stone.
Reports positions where solver-to-move has exactly one best (win) move and opponent-first would beat solver."""
import sys
import itertools
from gotools import *
import designs


def analyze(prob, board, first, solver, objective, maxnodes=2_000_000):
    res, overall, stats = classify(prob, board, first, solver, objective, maxnodes=maxnodes)
    if any(v == -2 for v in overall.values()):
        return None
    wins = sorted(m for m, v in res.items() if v == 'win')
    return res, wins


def main():
    name = sys.argv[1]
    pts = [p for p in sys.argv[2].split(',') if p]
    maxmut = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    d = designs.D[name]
    b0, region0, safe0, target0 = diagram(d['rows'])
    if d.get('target'):
        target0 = {sgf2i(s) for s in d['target']}
    att = d['att']
    dfn = opp(att)
    first, solver, objective = d['first'], d['solver'], d['objective']
    opts = [EMPTY, dfn, att]
    idxs = [sgf2i(p) for p in pts]
    seen = 0
    for k in range(0, maxmut + 1):
        for combo in itertools.combinations(idxs, k):
            for vals in itertools.product(opts, repeat=k):
                b = b0.copy()
                region = set(region0)
                changed = False
                for i, v in zip(combo, vals):
                    if b.b[i] == v:
                        break
                    b.b[i] = v
                    region.add(i)
                    changed = True
                else:
                    if k and not changed:
                        continue
                    # legality: no chain without liberties
                    bad = False
                    for i in range(361):
                        if b.b[i]:
                            st, lb = b.chain(i)
                            if not lb:
                                bad = True
                                break
                    if bad:
                        continue
                    tgt = {i for i in target0 if b.b[i] == dfn}
                    if not tgt:
                        continue
                    prob = Problem(b, region, safe0, tgt, att)
                    r = analyze(prob, b, first, solver, objective)
                    if r is None:
                        continue
                    res, wins = r
                    if len(wins) != 1:
                        continue
                    # opponent first should defeat solver
                    st = status(prob, b, opp(first), solver, objective)
                    if st == 'win':
                        continue
                    seen += 1
                    desc = ' '.join('%s=%s' % (i2sgf(i), '.XO'[v]) for i, v in zip(combo, vals))
                    nl = sum(1 for v in res.values() if v != 'win')
                    print('[%s] key=%s  opp-first=%s  others=%s' % (desc, wins[0], st,
                          ' '.join('%s:%s' % (m, v) for m, v in sorted(res.items()) if v != 'lose')), flush=True)
    print('found', seen)


if __name__ == '__main__':
    main()
