"""Generator v2: larger, more irregular positions; records K=1 tree metrics."""
import sys, random, json, time
sys.path.insert(0, 'scratch')
from gen import n4, n8, components, normalise, to_diag
from build import *

def gen_position(rng, mode):
    off = 0 if mode == 'corner' else 2
    def inb(c): return 0 <= c[0] < 19 and 0 <= c[1] < 19
    size = rng.randint(7, 12)
    if mode == 'corner':
        start = (0, 0); maxx, maxy, minx = rng.randint(3, 6), rng.randint(1, 3), 0
    else:
        minx = off + 1
        start = (minx + rng.randint(0, 3), 0); maxx, maxy = minx + rng.randint(4, 7), rng.randint(1, 2)
    E = {start}; tries = 0
    while len(E) < size and tries < 300:
        tries += 1
        c = rng.choice(sorted(E)); d = rng.choice(n4(c))
        if d[0] < minx or d[0] > maxx or d[1] < 0 or d[1] > maxy: continue
        if d[1] >= 2 and rng.random() < 0.5: continue
        E.add(d)
    shell = set()
    for c in E:
        for d in n8(c):
            if inb(d) and d not in E: shell.add(d)
    wall = set()
    for c in shell:
        for d in n8(c):
            if inb(d) and d not in E and d not in shell: wall.add(d)
    grid = {}
    for c in E: grid[c] = '+'
    for c in shell: grid[c] = '@'
    for c in wall: grid[c] = 'X'
    k = rng.choice([1, 1, 2, 2, 3])
    sh = sorted(shell); rng.shuffle(sh); removed = 0
    for c in sh:
        if removed >= k: break
        if c[1] == 0 or c[0] == 0 or rng.random() < 0.5:
            grid[c] = '+'; removed += 1
    inner = sorted(E); rng.shuffle(inner)
    nb = rng.choice([1, 1, 2, 2, 3]); nw = rng.choice([0, 0, 1, 1, 2])
    for c in inner[:nb]: grid[c] = 'x'
    for c in inner[nb:nb + nw]: grid[c] = 'o'
    if rng.random() < 0.3:
        ws = [c for c in sorted(wall) if c[1] >= 1 and any(grid.get(d) == '@' for d in n4(c))]
        if ws:
            c = rng.choice(ws); grid[c] = '+'
            for d in n8(c):
                if inb(d) and d not in grid: grid[d] = 'X'
    return grid

def pline(n):
    best=[]
    for c in n.children:
        l=[c.move]+pline(c)
        if len(l)>len(best): best=l
    return best

if __name__ == '__main__':
    mode, seed, count, outfn = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    rng = random.Random(seed); seen = set(); out = open(outfn, 'w'); t0 = time.time(); n = 0
    while n < count:
        g = normalise(gen_position(rng, mode))
        if g is None: continue
        diag = to_diag(g)
        if diag in seen: continue
        seen.add(diag); n += 1
        nreg = sum(1 for ch in diag if ch == '+')
        if nreg > 13 or nreg < 5: continue
        for first in 'BW':
            p = Problem(diag, defender='W', first=first, maxnodes=500000)
            try:
                st, v = p.query([])
                if st or any(x < 0 for x in v.values()): continue
                wins = [m for m, x in v.items() if x == 2 and m != 'pass']
                if v.get('pass', 0) == 2 or len(wins) != 1: continue
                kos = [m for m, x in v.items() if x == 1 and m != 'pass']
                b = B2(p, K=1, wrong_root=[], inner={}, inner_wrong=0, max_right_len=13)
                root = b.build()
                pv = pline(root)
                traps = 0
                for m, x in v.items():
                    if m == 'pass' or x >= 2: continue
                    st2, v2 = p.query([m])
                    if st2: continue
                    refs = [r for r, y in v2.items() if y < 2 and r != 'pass']
                    if len(refs) <= 1: traps += 1
                out.write(json.dumps(dict(diag=diag, first=first, key=wins[0], kos=kos, nmoves=len(v)-1, rnodes=count_nodes(root), pv=pv, traps=traps)) + '\n'); out.flush()
            except Exception as e:
                pass
            finally:
                p.close()
    out.write('#done %d in %.0fs\n' % (n, time.time() - t0))
