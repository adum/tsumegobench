import random, sys, json
import tl
from tl import *
from gen import cheb, polyomino, legal_setup
from mut import evaluate
tl.TIMEOUT = 15
def make(rng, kind):
    k = rng.randint(6, 10)
    I = polyomino(rng, k, kind, 6, 3 if kind == 'corner' else 2)
    D = cheb(I, 19, 19); A = cheb(I | D, 19, 19)
    sd, sa = set(D), set(A); Il = sorted(I)
    for _ in range(rng.choice([0, 1, 1, 2, 2])):
        p = rng.choice(sorted(D))
        if p in sd:
            sd.discard(p)
            if rng.random() < 0.5: sa.add(p)
    for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
        sa.add(rng.choice(Il))
    for _ in range(rng.choice([0, 0, 1])):
        p = rng.choice(Il)
        if p not in sa: sd.add(p)
    return sd, sa, set(I) | set(D)
seed = int(sys.argv[1]); n = int(sys.argv[2]); kind = sys.argv[3]
rng = random.Random(seed)
out = open(f'g4_{kind}_{seed}.jsonl', 'w')
for it in range(n):
    defcolor = rng.choice([BLACK, WHITE])
    sd, sa, region = make(rng, kind)
    if len(region) > 24: continue
    AB, AW = [], []
    for (x, y) in sd: (AB if defcolor == BLACK else AW).append(chr(97 + x) + chr(97 + y))
    for (x, y) in sa: (AW if defcolor == BLACK else AB).append(chr(97 + x) + chr(97 + y))
    reg = [chr(97 + x) + chr(97 + y) for (x, y) in region]
    sp0 = Spec(AB, AW, reg, 'B', 'live', [])
    if not legal_setup(sp0): continue
    bd = sp0.board(); best = None; seen = set()
    for p in AB + AW:
        i = s2i(p)
        if bd.b[i] == defcolor and i not in seen:
            st, lb = bd.chain(i); seen.update(st)
            if best is None or len(st) > len(best): best = st
    if best is None or len(best) < 5: continue
    key = i2s(best[0])
    for goal in ('live', 'kill'):
        solver = defcolor if goal == 'live' else opp(defcolor)
        sp = Spec(AB, AW, reg, 'B' if solver == BLACK else 'W', goal, key, maxdepth=30)
        try: m = evaluate(sp)
        except Exception: m = None
        if m and (m['L'] >= 2 or m['tempt'] >= 4):
            out.write(json.dumps(dict(AB=AB, AW=AW, region=reg, key=key, goal=goal, solver=solver, **m)) + '\n'); out.flush()
