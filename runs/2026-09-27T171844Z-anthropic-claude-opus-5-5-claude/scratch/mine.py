"""Mine corner/side positions for tsumego candidates.
Defender wall = monotone staircase in top-left corner. Attacker wall hugs outside (safe).
Random perturbations add interior stones / gaps / edge hanes."""
import random
import sys
import time
from gotools import *


def staircase(rng, maxx=6, maxy=6):
    """Return list of wall points from top edge (x0,0) to left edge (0,y0), monotone.
    Path: start at (x0, 0), move down or left alternately until x==0."""
    x0 = rng.randint(3, maxx)
    pts = [(x0, 0)]
    x, y = x0, 0
    while x > 0:
        # choose to move down (y+1) or left (x-1)
        if y < maxy and (rng.random() < 0.45 or y == 0):
            y += 1
        else:
            x -= 1
        pts.append((x, y))
    return pts


def build_corner(rng, att, params):
    dfn = opp(att)
    b = Board()
    wall = staircase(rng, params.get('maxx', 6), params.get('maxy', 5))
    wallset = set(wall)
    # interior: points (x,y) that are "inside" : for each row y, x < min wall x in that row
    minx_row = {}
    for (x, y) in wall:
        minx_row[y] = min(minx_row.get(y, 99), x)
    maxy = max(y for x, y in wall)
    interior = set()
    for y in range(0, maxy + 1):
        lim = minx_row.get(y, 0)
        for x in range(0, lim):
            if (x, y) not in wallset:
                interior.add((x, y))
    # remove interior points that are "below" wall on left edge path: ensure interior bounded
    # wall endpoint on left edge is (0, y_end); interior rows beyond y_end none.
    for p in wall:
        b.b[xy2i(*p)] = dfn
    # attacker wall: all points adjacent (8-neighborhood) to wall that are outside interior and not wall
    outside = set()
    for (x, y) in wall:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if 0 <= q[0] < N and 0 <= q[1] < N and q not in wallset and q not in interior:
                    outside.add(q)
    # only orthogonally-adjacent outside points become attacker stones; diagonal ones too for solidity
    safe = set()
    for q in outside:
        b.b[xy2i(*q)] = att
        safe.add(xy2i(*q))
    region = {xy2i(*p) for p in interior}
    target = {xy2i(*p) for p in wall}
    # perturbations
    nper = rng.randint(params.get('minper', 1), params.get('maxper', 3))
    wall_inner = [p for p in wall]
    for _ in range(nper):
        r = rng.random()
        if r < 0.25 and len(interior) > 2:
            # attacker stone in interior
            p = rng.choice(sorted(interior))
            b.b[xy2i(*p)] = att
        elif r < 0.45 and len(interior) > 2:
            p = rng.choice(sorted(interior))
            b.b[xy2i(*p)] = dfn
            target.add(xy2i(*p))
        elif r < 0.65:
            # gap in wall (not endpoints)
            p = rng.choice(wall_inner[1:-1]) if len(wall_inner) > 2 else None
            if p:
                i = xy2i(*p)
                b.b[i] = EMPTY
                region.add(i)
                target.discard(i)
        elif r < 0.85:
            # attacker pushes into wall point (capturable attacker stone)
            p = rng.choice(wall_inner[1:-1]) if len(wall_inner) > 2 else None
            if p:
                i = xy2i(*p)
                b.b[i] = att
                region.add(i)
                target.discard(i)
        else:
            # edge hane: attacker stone on edge adjacent to wall endpoint inside
            end = rng.choice([wall[0], wall[-1]])
            if end[1] == 0:
                p = (end[0] - 1, 0)
            else:
                p = (0, end[1] - 1)
            if p in interior:
                b.b[xy2i(*p)] = att
    # region: include all interior points (stones in play too)
    return b, region, safe, target


def legal_setup(b):
    for i in range(N * N):
        if b.b[i]:
            st, lb = b.chain(i)
            if not lb:
                return False
    return True


def evaluate(b, region, safe, target, att, solver, maxnodes=3_000_000):
    dfn = opp(att)
    target = {i for i in target if b.b[i] == dfn}
    if not target:
        return None
    # target = largest defender chain among target stones (peripheral stones may be sacrificed)
    best = set()
    for i in target:
        st, lb = b.chain(i)
        if len(st) > len(best):
            best = st
    if len(best) < 3:
        return None
    target = best
    prob = Problem(b, region, safe, target, att)
    objective = 'kill' if solver == att else 'live'
    res, overall, stats = classify(prob, b, solver, solver, objective, maxnodes=maxnodes)
    if any(v == -2 for v in overall.values()) or not res:
        return None
    wins = sorted(m for m, v in res.items() if v == 'win')
    if len(wins) != 1 or wins[0] == 'pass':
        return None
    st = status(prob, b, opp(solver), solver, objective)
    if st == 'win':
        return None
    return prob, res, wins[0], st


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    rng = random.Random(seed)
    found = 0
    t0 = time.time()
    for it in range(count):
        att = rng.choice([BLACK, WHITE])
        solver = rng.choice([att, opp(att)])
        b, region, safe, target = build_corner(rng, att, {})
        if not legal_setup(b):
            continue
        if len(region) > 16 or len(region) < 4:
            continue
        r = evaluate(b, region, safe, target, att, solver)
        if r is None:
            continue
        prob, res, key, st = r
        found += 1
        others = ' '.join('%s:%s' % (m, v) for m, v in sorted(res.items()) if v not in ('lose', 'win'))
        print('#%d seed=%d it=%d solver=%s obj=%s key=%s opp-first=%s others=[%s] region=%d' % (
            found, seed, it, CNAME[solver], 'kill' if solver == att else 'live', key, st, others, len(region)))
        print(b.show(0, 0, 8, 7, marks={sgf2i(key): '*'}))
        sys.stdout.flush()
    print('done', found, time.time() - t0)


if __name__ == '__main__':
    main()


def side_wall(rng, width_min=5, width_max=9, maxh=3):
    """Defender wall on top side: from (x1,0) down to height h, across to x2, up to (x2,0).
    Heights vary per column between 1..maxh (profile). Returns wall points and interior."""
    w = rng.randint(width_min, width_max)
    x1 = 3
    x2 = x1 + w
    # profile: height of wall at each interior column (wall at y=h, interior y<h)
    hs = []
    h = rng.randint(1, 2)
    for x in range(x1 + 1, x2):
        if rng.random() < 0.3:
            h = max(1, min(maxh, h + rng.choice([-1, 1])))
        hs.append(h)
    wall = set()
    interior = set()
    # left and right columns
    for y in range(0, hs[0] + 1):
        wall.add((x1, y))
    for y in range(0, hs[-1] + 1):
        wall.add((x2, y))
    for k, x in enumerate(range(x1 + 1, x2)):
        wall.add((x, hs[k]))
        for y in range(0, hs[k]):
            interior.add((x, y))
    # fill vertical connections between different heights
    for k in range(len(hs) - 1):
        xa, xb = x1 + 1 + k, x1 + 2 + k
        if hs[k] < hs[k + 1]:
            for y in range(hs[k], hs[k + 1]):
                if (xa, y) not in interior:
                    wall.add((xa, y))
        elif hs[k] > hs[k + 1]:
            for y in range(hs[k + 1], hs[k]):
                if (xb, y) not in interior:
                    wall.add((xb, y))
    interior -= wall
    return sorted(wall), interior


def build_side(rng, att, params):
    dfn = opp(att)
    b = Board()
    wall, interior = side_wall(rng, params.get('wmin', 5), params.get('wmax', 8), params.get('maxh', 2))
    wallset = set(wall)
    for p in wall:
        b.b[xy2i(*p)] = dfn
    outside = set()
    for (x, y) in wall:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if 0 <= q[0] < N and 0 <= q[1] < N and q not in wallset and q not in interior:
                    outside.add(q)
    safe = set()
    for q in outside:
        b.b[xy2i(*q)] = att
        safe.add(xy2i(*q))
    region = {xy2i(*p) for p in interior}
    target = {xy2i(*p) for p in wall}
    ends = [min(wall), max(wall)]
    nper = rng.randint(params.get('minper', 1), params.get('maxper', 3))
    inner_wall = [p for p in wall if p[1] > 0]
    for _ in range(nper):
        r = rng.random()
        if r < 0.25 and len(interior) > 2:
            p = rng.choice(sorted(interior))
            b.b[xy2i(*p)] = att
        elif r < 0.45 and len(interior) > 2:
            p = rng.choice(sorted(interior))
            b.b[xy2i(*p)] = dfn
            target.add(xy2i(*p))
        elif r < 0.6 and inner_wall:
            p = rng.choice(inner_wall)
            i = xy2i(*p)
            b.b[i] = EMPTY
            region.add(i)
            target.discard(i)
        elif r < 0.75 and inner_wall:
            p = rng.choice(inner_wall)
            i = xy2i(*p)
            b.b[i] = att
            region.add(i)
            target.discard(i)
        else:
            # remove a wall stone at the edge end (defender end stone on first line) -> attacker hane there
            e = rng.choice([p for p in wall if p[1] == 0])
            i = xy2i(*e)
            b.b[i] = att
            region.add(i)
            target.discard(i)
    return b, region, safe, target
