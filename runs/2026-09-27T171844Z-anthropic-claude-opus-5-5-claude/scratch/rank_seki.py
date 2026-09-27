import re, sys
import gotools
gotools.FAST = True
from gotools import *
import enumw, etree, gentree
from mine5 import tree_stats, branch_count

fn, wall = sys.argv[1], sys.argv[2]
rows = []
for L in open(fn):
    m = re.match(r'#(\d+) wall=(\w+) key=(\w+) B=([\w,]+) W=([\w-]+)', L)
    if not m:
        continue
    idx, w, key, bs, ws = m.groups()
    b0, region, safe, target = diagram(enumw.WALLS[wall])
    b = b0.copy()
    for s in bs.split(','):
        b.b[sgf2i(s)] = BLACK
    if ws != '-':
        b.b[sgf2i(ws)] = WHITE
    tgt = set()
    for i in region:
        if b.b[i] == WHITE:
            st, lb = b.chain(i)
            if len(st) > len(tgt):
                tgt = st
    prob = Problem(b, region, safe, tgt, BLACK)
    etree._cache.clear(); etree._scache.clear()
    try:
        frags = gentree.gen(prob, b, WHITE, 'seki', maxans=2)
        d, n, s = tree_stats(frags)
        bc = branch_count(prob, b, WHITE, 'seki')
    except Exception as e:
        continue
    rows.append((d, -n, idx, key, bs, ws, n, bc, s))
rows.sort(reverse=True)
for d, _, idx, key, bs, ws, n, bc, s in rows[:25]:
    print('#%s key=%s B=%s W=%s depth=%d nodes=%d branch=%d %s' % (idx, key, bs, ws, d, n, bc, s[:150]))
