"""Rank enumeration hits by key surprise and depth. Usage: python3 rank.py files..."""
import re
import sys
from gotools import *
import enumw


def parse(fn):
    out = []
    lines = open(fn).read().split('\n')
    for i, L in enumerate(lines):
        if not L.startswith('#'):
            continue
        m = re.search(r'wall=(\w+) obj=(\w+) key=(\w+) depth=(\d+) nodes=(\d+) branch=(\d+) B=([\w,]+) W=([\w-]+) gap=([\w-]+)', L)
        if not m:
            continue
        wall, obj, key, d, n, br, bs, ws, gap = m.groups()
        tree = ''
        for j in range(i + 1, min(i + 12, len(lines))):
            if lines[j].startswith('TREE '):
                tree = lines[j][5:]
                break
        out.append(dict(fn=fn, hdr=L, wall=wall, obj=obj, key=key, depth=int(d), nodes=int(n), branch=int(br),
                        bs=bs.split(','), ws=ws, gap=gap, tree=tree))
    return out


def board_of(c):
    b0, region, safe, target = diagram(enumw.WALLS[c['wall']])
    b = b0.copy()
    for s in c['bs']:
        b.b[sgf2i(s)] = BLACK
    if c['ws'] != '-':
        b.b[sgf2i(c['ws'])] = WHITE
    if c['gap'] != '-':
        b.b[sgf2i(c['gap'])] = EMPTY
    return b


def features(c):
    b = board_of(c)
    solver = BLACK if c['obj'] == 'kill' else WHITE
    k = sgf2i(c['key'])
    x, y = k % N, k // N
    first = (x == 0 or y == 0)
    adj_own = any(b.b[q] == solver for q in neighbors(k))
    nb = b.copy()
    selfatari = False
    try:
        nb.play(k, solver)
        st, lb = nb.chain(k)
        selfatari = len(lb) == 1
    except IllegalMove:
        pass
    gapkey = (c['gap'] != '-' and c['key'] == c['gap'])
    return first, not adj_own, selfatari, gapkey


if __name__ == '__main__':
    allc = []
    for fn in sys.argv[1:]:
        try:
            allc += parse(fn)
        except FileNotFoundError:
            pass
    rows = []
    for c in allc:
        first, placement, sa, gapkey = features(c)
        score = c['depth'] * 2 + 3 * first + 3 * placement + 4 * sa - 6 * gapkey - c['branch'] - c['nodes'] / 10.0
        rows.append((score, c, first, placement, sa, gapkey))
    rows.sort(key=lambda r: -r[0])
    for score, c, first, placement, sa, gapkey in rows[:40]:
        print('%5.1f %-6s %-4s key=%s d=%d n=%d br=%d B=%s W=%s gap=%s %s%s%s%s' % (
            score, c['wall'], c['obj'], c['key'], c['depth'], c['nodes'], c['branch'], ','.join(c['bs']), c['ws'], c['gap'],
            'FIRST ' if first else '', 'PLACE ' if placement else '', 'SELFATARI ' if sa else '', 'GAPKEY' if gapkey else ''))
