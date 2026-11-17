"""Random generator of enclosed eye-space positions (attacker Black, defender White, authoring frame).
usage: python3 scratch/gen.py <mode corner|side> <seed> <count> <outfile>
"""
import sys, random, json, time
sys.path.insert(0, 'scratch')
from tsu import *
from enumv import analyse, depth_metric


def n4(c):
    x, y = c
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def n8(c):
    x, y = c
    return [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def gen_position(rng, mode):
    W, H = (7, 4) if mode == 'corner' else (9, 3)
    off = 0 if mode == 'corner' else 2   # side frames start at column 2 so the wall fits on the left
    def inb(c):
        return 0 <= c[0] < 19 and 0 <= c[1] < 19
    size = rng.randint(6, 11)
    # grow eye space from a seed on the edge
    if mode == 'corner':
        start = (0, 0)
        maxx, maxy = rng.randint(3, 5), rng.randint(1, 2)
        minx = 0
    else:
        minx = off + 1
        start = (minx + rng.randint(0, 3), 0)
        maxx, maxy = minx + rng.randint(4, 6), rng.randint(1, 2)
    E = {start}
    tries = 0
    while len(E) < size and tries < 200:
        tries += 1
        c = rng.choice(sorted(E))
        d = rng.choice(n4(c))
        if d[0] < minx or d[0] > maxx or d[1] < 0 or d[1] > maxy:
            continue
        # bias to the edge rows
        if d[1] == 2 and rng.random() < 0.5:
            continue
        E.add(d)
    shell = set()
    for c in E:
        for d in n8(c):
            if inb(d) and d not in E:
                shell.add(d)
    wall = set()
    for c in shell:
        for d in n8(c):
            if inb(d) and d not in E and d not in shell:
                wall.add(d)
    grid = {}
    for c in E:
        grid[c] = '+'
    for c in shell:
        grid[c] = '@'
    for c in wall:
        grid[c] = 'X'
    # perturbations
    # 1. remove shell stones (prefer edge / first-line ones)
    k = rng.choice([0, 0, 1, 1, 1, 2, 2])
    sh = sorted(shell)
    rng.shuffle(sh)
    removed = 0
    for c in sh:
        if removed >= k:
            break
        # only remove stones that touch the eye space orthogonally or sit on the edge
        if c[1] == 0 or c[0] == 0 or rng.random() < 0.35:
            grid[c] = '+'
            removed += 1
    # 2. stones inside
    inner = sorted(E)
    nb = rng.choice([0, 0, 1, 1, 2])
    nw = rng.choice([0, 0, 0, 1, 1, 2])
    rng.shuffle(inner)
    for c in inner[:nb]:
        grid[c] = 'x'
    for c in inner[nb:nb + nw]:
        grid[c] = 'o'
    # 3. outside liberty
    if rng.random() < 0.35:
        ws = [c for c in sorted(wall) if c[1] >= 1 and any(grid.get(d) == '@' for d in n4(c))]
        if ws:
            c = rng.choice(ws)
            grid[c] = '+'
            for d in n4(c):
                if inb(d) and d not in grid:
                    grid[d] = 'X'
            for d in n8(c):
                if inb(d) and d not in grid:
                    grid[d] = 'X'
    return grid


def components(grid, chars):
    pts = [c for c, ch in grid.items() if ch in chars]
    seen = set()
    comps = []
    for c in pts:
        if c in seen:
            continue
        comp = {c}
        st = [c]
        while st:
            q = st.pop()
            for d in n4(q):
                if d in grid and grid[d] in chars and d not in comp:
                    comp.add(d); st.append(d)
        seen |= comp
        comps.append(comp)
    return comps


def normalise(grid):
    """target = largest white component; other white stones 'o'. reject if any group in atari/dead."""
    comps = components(grid, '@o')
    if not comps:
        return None
    comps.sort(key=len, reverse=True)
    main = comps[0]
    if len(comps) > 1 and len(comps[1]) * 2 > len(main):
        return None
    for c, ch in list(grid.items()):
        if ch in '@o':
            grid[c] = '@' if c in main else 'o'
    # liberties check
    def libs(comp):
        s = set()
        for q in comp:
            for d in n4(q):
                if 0 <= d[0] < 19 and 0 <= d[1] < 19 and grid.get(d, '.') in '+.a':
                    s.add(d)
        return s
    for comp in components(grid, '@o'):
        if len(libs(comp)) < 2:
            return None
    for comp in components(grid, 'Xx'):
        if len(libs(comp)) < 2:
            return None
    return grid


def to_diag(grid):
    w = max(c[0] for c in grid) + 2
    hgt = max(c[1] for c in grid) + 2
    rows = []
    for y in range(hgt):
        rows.append(''.join(grid.get((x, y), '.') for x in range(w)))
    return '\n'.join(rows)


def trap_metric(p, best=2):
    st, v = p.query([])
    traps = 0
    for m, x in v.items():
        if m == 'pass' or x >= best:
            continue
        st2, v2 = p.query([m])
        if st2:
            continue
        refs = [r for r, y in v2.items() if y < best and r != 'pass']
        if v2.get('pass', 2) >= best and len(refs) <= 2:
            traps += 1
    return traps


MAXN = 600000

if __name__ == '__main__':
    mode, seed, count, outfn = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    rng = random.Random(seed)
    seen = set()
    out = open(outfn, 'w')
    t0 = time.time()
    n = 0
    while n < count:
        g = gen_position(rng, mode)
        g = normalise(g)
        if g is None:
            continue
        diag = to_diag(g)
        if diag in seen:
            continue
        seen.add(diag)
        n += 1
        nreg = sum(1 for ch in diag if ch == '+')
        if nreg > 13 or nreg < 4:
            continue
        try:
            res = analyse(diag, maxnodes=MAXN)
        except Exception as e:
            continue
        for first, win, kos, pv, dm, nm in res:
            p = Problem(diag, defender='W', first=first, maxnodes=MAXN)
            try:
                tr = trap_metric(p)
            finally:
                p.close()
            out.write(json.dumps(dict(diag=diag, first=first, key=win, kos=kos, passval=pv, depth=dm, moves=nm, traps=tr)) + '\n')
            out.flush()
    out.write('#done %d in %.0fs\n' % (n, time.time() - t0))
