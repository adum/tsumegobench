import sys
from gotools import *
from design import load
d, prob = load(sys.argv[1])
for s in sys.argv[3:]:
    b = prob.board.copy(); c = d['first']
    for m in s.split(','):
        b.play(sgf2i(m), c); c = opp(c)
    # solver (defender) to move; can it live (non-strict) if it wins all kos?
    r, mv, st = prob.solve(b, c, opp(prob.attacker), 0, maxnodes=int(sys.argv[2]), allmoves=False)
    print(s, 'to move', CNAME[c], 'defender-wins-kos result r=%s' % r, st, flush=True)
