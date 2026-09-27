import sys
import gotools
gotools.SECONDARY_MAXNODES = int(sys.argv[2]) if len(sys.argv) > 2 else 30_000_000
from gotools import *
from design import load
d, prob = load(sys.argv[1])
seqs = sys.argv[3:] or ['']
for s in seqs:
    b = prob.board.copy(); c = d['first']
    for m in [x for x in s.split(',') if x]:
        b.play(sgf2i(m), c); c = opp(c)
    res, overall, stats = classify(prob, b, c, d['solver'], d['objective'], maxnodes=30_000_000)
    print(s or '(root)', 'to move', CNAME[c], sorted(res.items()), overall, stats, flush=True)
