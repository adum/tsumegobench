import random, sys, json, time
import tl
from tl import *
from gen import cheb, polyomino, legal_setup
tl.TIMEOUT = 20
def make(rng, kind):
    k = rng.randint(5, 9)
    I = polyomino(rng, k, kind, 6, 3)
    D = cheb(I, 19, 19); A = cheb(I | D, 19, 19)
    sd, sa = set(D), set(A); Il = sorted(I)
    for _ in range(rng.choice([0, 1, 1, 2])):
        p = rng.choice(sorted(D))
        if p in sd:
            sd.discard(p)
            if rng.random() < 0.4: sa.add(p)
    for _ in range(rng.choice([1, 2, 2, 3, 3, 4])):
        p = rng.choice(Il); sa.add(p)
    for _ in range(rng.choice([0, 0, 1])):
        p = rng.choice(Il)
        if p not in sa: sd.add(p)
    return sd, sa, set(I) | set(D)
seed = int(sys.argv[1]); n = int(sys.argv[2]); kind = sys.argv[3]
rng = random.Random(seed)
out = open(f'seki_{kind}_{seed}.jsonl', 'w')
for it in range(n):
    defcolor = rng.choice([BLACK, WHITE])
    sd, sa, region = make(rng, kind)
    AB, AW = [], []
    for (x, y) in sd: (AB if defcolor == BLACK else AW).append(chr(97 + x) + chr(97 + y))
    for (x, y) in sa: (AW if defcolor == BLACK else AB).append(chr(97 + x) + chr(97 + y))
    reg = [chr(97 + x) + chr(97 + y) for (x, y) in region]
    sp = Spec(AB, AW, reg, 'B' if defcolor == BLACK else 'W', 'live', [])
    if not legal_setup(sp): continue
    bd = sp.board(); best = None; seen = set()
    for p in AB + AW:
        i = s2i(p)
        if bd.b[i] == defcolor and i not in seen:
            st, lb = bd.chain(i); seen.update(st)
            if best is None or len(st) > len(best): best = st
    if best is None or len(best) < 4: continue
    key = i2s(best[0])
    sp = Spec(AB, AW, reg, 'B' if defcolor == BLACK else 'W', 'live', key, maxdepth=30)
    try:
        an = run(sp, sp.board(), defcolor)
        wins = [m for m, v in an.items() if v[0] == 'W']
        if len(wins) != 1 or any(v[0] == 'U' for v in an.values()): continue
        an2 = run(sp, sp.board(), defcolor, strict=True)
        if any(v[0] == 'W' for v in an2.values()): continue
        # attacker first should kill
        ks = sp.with_(solver='W' if defcolor == BLACK else 'B'); ks.goal = 'kill'
        an3 = run(ks, ks.board(), opp(defcolor))
        if not any(v[0] == 'W' for v in an3.values()): continue
    except Exception as e:
        continue
    rec = dict(AB=AB, AW=AW, region=reg, key=key, goal='live', defcolor=defcolor, move=wins[0], depth=an[wins[0]][1])
    out.write(json.dumps(rec) + '\n'); out.flush()
