import sys
import tl
from tl import *
from auto import *
from d import load
from probs import P
tl.TIMEOUT = 600
sp = P[sys.argv[1]] if sys.argv[1] in P else load(sys.argv[1])
pre = sys.argv[2:]
bd = sp.board(); c = sp.solver; ko = -1
for m in pre: bd, ko = apply(bd, m, c); c = opp(c)
print(show(bd, set(sp.region)))
an = run(sp, bd, c, ko)
wins = sorted([(m, v[1]) for m, v in an.items() if v[0] == 'W'])
print('solver' if c == sp.solver else 'opp', 'to move; solver-winning moves:', wins, ' U:', [m for m, v in an.items() if v[0]=='U'])
os_ = opp_spec(sp)
a0 = run(os_, bd, opp(sp.solver) if c == sp.solver else c, ko) if c == sp.solver else None
if a0: print('if opponent moved first, its winning moves:', sorted(m for m, v in a0.items() if v[0] == 'W'))
if c == sp.solver and len(wins) >= 1:
    A = Auto(sp, 3, maxply=11)
    t = A.build_right(bd, c, ko, 0, [])
    show_tree(t, 1, 'B' if c == BLACK else 'W')
    W = AutoWrong(sp)
    rows = []
    for m, v in an.items():
        if v[0] == 'W' or m == 'pass': continue
        nb, nko = apply(bd, m, c)
        refs = W.refutations(nb, opp(c), nko)
        rows.append((len(refs), m, refs[:3]))
    rows.sort()
    print('strict (non-seki) wins:', sorted(m for m, v in run(sp, bd, c, ko, strict=True).items() if v[0]=='W'))
    print('wrong moves (fewest refutations first):')
    for r in rows[:10]: print('  ', r)
