"""Mutation search for harder problems."""
import random, sys, json, glob, time
import tl
from tl import *
from gen import legal_setup
tl.TIMEOUT = 20

def evaluate(sp):
    """Return metrics dict or None if not a proper problem."""
    bd = sp.board()
    if not legal_setup(sp): return None
    d = sp.solver if sp.goal == 'live' else opp(sp.solver)
    if any(bd.b[k] != d for k in sp.key): return None
    an = run(sp, bd, sp.solver)
    wins = [m for m, v in an.items() if v[0] == 'W']
    if len(wins) != 1 or wins[0] == 'pass': return None
    if any(v[0] == 'U' for v in an.values()): return None
    # hot: opponent first succeeds
    os_ = sp.with_(solver='B' if sp.solver == WHITE else 'W'); os_.goal = 'kill' if sp.goal == 'live' else 'live'
    a0 = run(os_, bd, opp(sp.solver))
    if not any(v[0] == 'W' for v in a0.values()): return None
    # tempting wrong moves: exactly one refutation
    tempt = 0
    for m, v in an.items():
        if v[0] == 'W' or m == 'pass': continue
        nb, nko = apply(bd, m, sp.solver)
        a1 = run(sp, nb, opp(sp.solver), nko)
        refs = [k for k, x in a1.items() if x[0] != 'W']
        if len(refs) == 1: tempt += 1
    # principal variation: strongest defense, count unique non-obvious solver moves
    L = 0; line = [wins[0]]
    cur, ko = apply(bd, wins[0], sp.solver)
    for step in range(6):
        a = run(sp, cur, opp(sp.solver), ko)
        cand = sorted(((v[1], m) for m, v in a.items() if m != 'pass'), reverse=True)
        if not cand: break
        dmax, rep = cand[0]
        nb, nko = apply(cur, rep, opp(sp.solver))
        if any(nb.b[k] != d for k in sp.key): break
        a2 = run(sp, nb, sp.solver, nko)
        w2 = [m for m, v in a2.items() if v[0] == 'W' and m != 'pass']
        if a2.get('pass', ('L',))[0] == 'W' or len(w2) != 1: break
        mv = w2[0]
        # obvious? captures or saves atari
        i = s2i(mv); t = nb.copy(); cap = t.play(i, sp.solver)
        obvious = bool(cap) or any(nb.b[q] == sp.solver and len(nb.chain(q)[1]) == 1 for q in NEI[i])
        if not obvious: L += 1
        line += [rep, mv]
        cur, ko = apply(nb, mv, sp.solver)
    return dict(L=L, tempt=tempt, move=wins[0], line=line)

def mutate(rng, AB, AW, region, key):
    AB, AW = set(AB), set(AW)
    reg = sorted(region)
    for _ in range(rng.choice([1, 1, 2])):
        p = rng.choice(reg)
        if p in key: continue
        r = rng.random()
        if p in AB or p in AW:
            AB.discard(p); AW.discard(p)
            if r < 0.3: (AB if rng.random() < 0.5 else AW).add(p)
        else:
            (AB if r < 0.5 else AW).add(p)
    return sorted(AB), sorted(AW)

if __name__ == '__main__':
    seed = int(sys.argv[1]); iters = int(sys.argv[2]); src = sys.argv[3]
    rng = random.Random(seed)
    recs = [json.loads(l) for f in glob.glob(src) for l in open(f)]
    out = open(f'mut_{seed}.jsonl', 'w')
    while True:
        r = rng.choice(recs)
        solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
        sp = Spec(r['AB'], r['AW'], r['region'], 'B' if solver == 1 else 'W', r['goal'], r['key'], maxdepth=30)
        try: m = evaluate(sp)
        except Exception: m = None
        if m: break
    score = m['L'] * 3 + m['tempt']
    best = (score, sp.AB, sp.AW, m)
    for it in range(iters):
        AB, AW = mutate(rng, sp.AB, sp.AW, r['region'], [r['key']])
        s2 = Spec(AB, AW, r['region'], 'B' if sp.solver == BLACK else 'W', r['goal'], r['key'], maxdepth=30)
        try: m2 = evaluate(s2)
        except Exception: m2 = None
        if not m2: continue
        sc = m2['L'] * 3 + m2['tempt']
        if sc >= score or rng.random() < 0.1:
            sp, score = s2, sc
            out.write(json.dumps(dict(AB=AB, AW=AW, region=r['region'], key=r['key'], goal=r['goal'],
                                      solver=sp.solver, score=sc, **m2)) + '\n'); out.flush()
        if it % 200 == 199:
            # restart from a new random seed record
            while True:
                r = rng.choice(recs)
                solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
                sp = Spec(r['AB'], r['AW'], r['region'], 'B' if solver == 1 else 'W', r['goal'], r['key'], maxdepth=30)
                try: m = evaluate(sp)
                except Exception: m = None
                if m: break
            score = m['L'] * 3 + m['tempt']
