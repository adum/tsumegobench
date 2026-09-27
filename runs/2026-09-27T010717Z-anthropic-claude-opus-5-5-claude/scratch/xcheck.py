import sys, time
from probs import *
from registry import REG
import solver as S
for nn in sys.argv[1:]:
    name, tf, T = REG[nn]
    sp = tspec(P[name], T)
    bd = sp.board()
    b2 = S.Board(bd.b[:], bd.h)
    s = S.Solver(b2, sp.region, sp.solver, sp.goal, sp.key, maxdepth=40)
    t = time.time()
    w = s.winning_moves(b2, sp.solver)
    c = run(sp, bd, sp.solver)
    pw = sorted(m for m, v in w.items() if v)
    cw = sorted(m for m, v in c.items() if v[0] == 'W')
    print(nn, 'python:', pw, 'C:', cw, 'agree' if pw == cw else 'DISAGREE', round(time.time() - t, 1), 's', 'depthhit' if s.depth_hit else '')
