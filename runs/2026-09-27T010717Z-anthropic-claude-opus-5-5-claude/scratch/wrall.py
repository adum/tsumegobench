import sys
from probs import *
from auto import *
sp = P[sys.argv[1]]
A = AutoWrong(sp)
pre = []
args = sys.argv[2:]
if '--' in args:
    i = args.index('--'); pre = args[:i]; args = args[i+1:]
for w in args:
    moves = pre + [w]
    bd = sp.board(); c = sp.solver; ko = -1
    for m in moves: bd, ko = apply(bd, m, c); c = opp(c)
    refs = A.refutations(bd, c, ko)
    print('==', ' '.join(moves), 'refutations:', refs)
    for r in refs[:3]:
        nb, nko = apply(bd, r[0], c)
        ans = A.answers(nb, opp(c), nko)
        print('   after', r[0], 'min answers:', ans[:3])
