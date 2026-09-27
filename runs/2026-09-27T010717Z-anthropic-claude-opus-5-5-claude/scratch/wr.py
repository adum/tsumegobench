import sys
from probs import *
from auto import *
sp = P[sys.argv[1]]
A = AutoWrong(sp)
moves = sys.argv[2:]
bd = sp.board(); c = sp.solver; ko = -1
for m in moves: bd, ko = apply(bd, m, c); c = opp(c)
if c != sp.solver:
    print('refutations:', A.refutations(bd, c, ko))
else:
    for r in A.answers(bd, c, ko)[:8]: print('  try', r)
