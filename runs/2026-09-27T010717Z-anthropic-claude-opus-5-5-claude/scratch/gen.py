"""Random candidate generator for corner/side life-and-death problems (top-left orientation)."""
import random, sys, json, time
BIG = False
from tl import *

def cheb(pts, W, H):
    out = set()
    for (x, y) in pts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                a, b = x + dx, y + dy
                if 0 <= a < W and 0 <= b < H: out.add((a, b))
    return out - set(pts)

def polyomino(rng, k, kind, maxw, maxh):
    # grow from an anchor touching the edge(s)
    if kind == 'corner': start = (0, 0)
    else: start = (rng.randint(4, 8), 0)
    cells = {start}
    while len(cells) < k:
        x, y = rng.choice(sorted(cells))
        dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 0), (-1, 0)])  # bias horizontal
        a, b = x + dx, y + dy
        if a < 0 or b < 0: continue
        if kind == 'corner' and (a > maxw or b > maxh): continue
        if kind == 'side' and (b > maxh or a < 1 or a > 17): continue
        cells.add((a, b))
    return cells

def make(rng, kind='corner'):
    if BIG:
        k = rng.randint(7, 12)
        I = polyomino(rng, k, kind, 7, 3 if kind == 'corner' else 2)
    else:
        k = rng.randint(4, 9)
        I = polyomino(rng, k, kind, 6, 3)
    W, H = 19, 19
    D = cheb(I, W, H)
    A = cheb(I | D, W, H)
    B = {}  # point -> 'D','A' or 'I'
    stones_def, stones_att = set(D), set(A)
    empty_reg = set(I)
    # perturb: remove some shell stones
    Dl = sorted(D)
    for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
        p = rng.choice(Dl)
        if p in stones_def:
            stones_def.discard(p)
            if rng.random() < 0.4: stones_att.add(p)
            else: empty_reg.add(p)
    if BIG:
        for p in Dl:
            if p in stones_def and not any((p[0]+dx, p[1]+dy) in I for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))):
                if rng.random() < 0.5: stones_def.discard(p); empty_reg.add(p)
    # attacker stones inside
    Il = sorted(I)
    for _ in range(rng.choice([0, 0, 1, 1, 2])):
        p = rng.choice(Il)
        if p in empty_reg: empty_reg.discard(p); stones_att.add(p)
    for _ in range(rng.choice([0, 0, 0, 1])):
        p = rng.choice(Il)
        if p in empty_reg: empty_reg.discard(p); stones_def.add(p)
    # corner-shell stones (diagonal corners) are sometimes omitted
    region = set(I) | set(D)
    return stones_def, stones_att, region

def to_spec(sd, sa, region, defcolor, solver_is_def):
    AB, AW = [], []
    for (x, y) in sd: (AB if defcolor == BLACK else AW).append(chr(97 + x) + chr(97 + y))
    for (x, y) in sa: (AW if defcolor == BLACK else AB).append(chr(97 + x) + chr(97 + y))
    return AB, AW, [chr(97 + x) + chr(97 + y) for (x, y) in region]

def legal_setup(sp):
    bd = sp.board()
    for i in range(N * N):
        if bd.b[i]:
            st, lb = bd.chain(i)
            if not lb: return False
    return True

def evaluate(sd, sa, region, defcolor):
    # key: largest defender chain
    AB, AW, reg = to_spec(sd, sa, region, defcolor, True)
    sp = Spec(AB, AW, reg, defcolor, 'live', [])
    bd = sp.board()
    if not legal_setup(sp): return None
    best = None
    seen = set()
    for p in AB + AW:
        i = s2i(p)
        if bd.b[i] == defcolor and i not in seen:
            st, lb = bd.chain(i); seen.update(st)
            if best is None or len(st) > len(best): best = st
    if best is None or len(best) < 4: return None
    key = i2s(best[0])
    res = {}
    for goal, solver in (('live', defcolor), ('kill', opp(defcolor))):
        s = Spec(AB, AW, reg, 'B' if solver == BLACK else 'W', goal, key, maxdepth=30)
        an = run(s, s.board(), solver)
        res[goal] = an
    return AB, AW, reg, key, res

if __name__ == '__main__':
    seed = int(sys.argv[1]); n = int(sys.argv[2]); kind = sys.argv[3]
    BIG = len(sys.argv) > 4
    import tl; tl.TIMEOUT = 20
    tag = 'big' if BIG else ''
    rng = random.Random(seed)
    out = open(f'cands{tag}_{kind}_{seed}.jsonl', 'w')
    t0 = time.time()
    for it in range(n):
        defcolor = rng.choice([BLACK, WHITE])
        sd, sa, region = make(rng, kind)
        if len(region) > (28 if BIG else 22): continue
        try:
            r = evaluate(sd, sa, region, defcolor)
        except Exception as e:
            continue
        if r is None: continue
        AB, AW, reg, key, res = r
        for goal in ('live', 'kill'):
            an = res[goal]
            wins = [(m, v[1]) for m, v in an.items() if v[0] == 'W']
            unk = [m for m, v in an.items() if v[0] == 'U']
            if len(wins) == 1 and not unk:
                other = res['kill' if goal == 'live' else 'live']
                # the other side moving first should also succeed (hot position)
                if not any(v[0] == 'W' for v in other.values()): continue
                rec = dict(AB=AB, AW=AW, region=reg, key=key, goal=goal, defcolor=defcolor,
                           move=wins[0][0], depth=wins[0][1],
                           nearmiss=sorted(v[1] for m, v in an.items() if v[0] == 'L')[-3:])
                out.write(json.dumps(rec) + '\n'); out.flush()
    print('done', time.time() - t0)
