import sys
from design import load
import etree
from gotools import *
name = sys.argv[1]
d, prob = load(name)
S = d['solver']; obj = d['objective']
for s in sys.argv[2:]:
    seq = s.split(',')
    b = prob.board.copy(); c = d['first']
    for m in seq:
        b = etree.after(b, m, c); c = opp(c)
    r = etree.labels(prob, b, c, S, obj)
    print(s, 'to move', CNAME[c], {k: v for k, v in r.items() if k == 'pass' or v != 'lose'})
