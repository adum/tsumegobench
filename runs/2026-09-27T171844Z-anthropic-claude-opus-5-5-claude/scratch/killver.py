import re, sys
import gotools
gotools.FAST = True
from gotools import *
import enumw, etree, gentree
from mine5 import tree_stats, branch_count

fn = sys.argv[1]
for L in open(fn):
    m = re.match(r'#(\d+) wall=(\w+) obj=live key=(\w+) depth=(\d+) nodes=(\d+) branch=(\d+) B=([\w,]+) W=([\w-]+) gap=([\w-]+)', L)
    if not m:
        continue
    idx, wall, key, d, n, br, bs, ws, gap = m.groups()
    b0, region, safe, target = diagram(enumw.WALLS[wall])
    b = b0.copy()
    for s in bs.split(','):
        b.b[sgf2i(s)] = BLACK
    if ws != '-':
        b.b[sgf2i(ws)] = WHITE
    if gap != '-':
        b.b[sgf2i(gap)] = EMPTY
    tgt = set()
    for i in region:
        if b.b[i] == WHITE:
            st, lb = b.chain(i)
            if len(st) > len(tgt):
                tgt = st
    prob = Problem(b, region, safe, tgt, BLACK)
    res, ov, st = classify(prob, b, BLACK, BLACK, 'kill', maxnodes=1_000_000)
    if ov.get('A') == -2:
        print('#%s abort' % idx); continue
    wins = [k for k, v in res.items() if v == 'win']
    if len(wins) != 1:
        print('#%s kill wins=%s' % (idx, wins)); continue
    etree._cache.clear(); etree._scache.clear()
    frags = gentree.gen(prob, b, BLACK, 'kill', maxans=2)
    dd, nn, s = tree_stats(frags)
    print('#%s liveKey=%s killKey=%s B=%s W=%s gap=%s depth=%d nodes=%d %s' % (idx, key, wins[0], bs, ws, gap, dd, nn, s[:160]), flush=True)
