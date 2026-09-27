import sys
from probs import *
from auto import opp_spec
sp = P[sys.argv[1]]; moves = sys.argv[2:]
osp = opp_spec(sp)
bd = sp.board(); c = sp.solver; ko = -1
for m in moves: bd, ko = apply(bd, m, c); c = opp(c)
cache = {}
def neither(b, col, k):
    key = (b.h, col, k)
    if key not in cache:
        a = run(sp, b, col, k, cmd='value')[0]
        o = run(osp, b, col, k, cmd='value')[0]
        cache[key] = (a != 'W' and o != 'W')
    return cache[key]
def is_ko_capture(b, mv, col):
    nb = b.copy(); cap = nb.play(s2i(mv), col)
    if cap and len(cap) == 1:
        st, lb = nb.chain(s2i(mv))
        return len(st) == 1 and len(lb) == 1
    return False
best = None
def dfs(b, col, k, line, depth):
    global best
    if best and len(line) >= len(best): return
    if depth == 0: return
    a = run(sp, b, col, k)
    for m, v in a.items():
        if m == 'pass': continue
        try: nb, nk = apply(b, m, col)
        except ValueError: continue
        if not neither(nb, opp(col), nk): continue
        if is_ko_capture(b, m, col):
            if best is None or len(line) + 1 < len(best): best = line + [m]
            continue
        dfs(nb, opp(col), nk, line + [m], depth - 1)
dfs(bd, c, ko, [], int(sys.argv[0] and 6))
print('ko line:', best)
