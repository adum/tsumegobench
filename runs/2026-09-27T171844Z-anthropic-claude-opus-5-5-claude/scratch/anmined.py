import sys
from gotools import *
import minedload, etree
fn, idx = sys.argv[1], int(sys.argv[2])
cs = minedload.parse_file(fn)
c = [c for c in cs if c['hdr'].startswith('#%d ' % idx)][0]
prob = minedload.to_problem(c)
print(c['hdr'])
xs = [i % 19 for i in range(361) if prob.board.b[i]]
print(prob.board.show(0, 0, max(xs) + 1, 5))
seq = [m for m in (sys.argv[3].split(',') if len(sys.argv) > 3 else []) if m]
b = prob.board.copy(); col = c['solver']
for m in seq:
    b = etree.after(b, m, col); col = opp(col)
if col == c['solver']:
    etree.etree(prob, b, c['solver'], c['objective'], maxdepth=int(sys.argv[4]) if len(sys.argv) > 4 else 8)
else:
    ok, th = etree.threats(prob, b, c['solver'], c['objective'])
    print('ok', ok)
    for om, w3, nb2, lab in th:
        print('  threat %s -> solver answers %s' % (om, w3))
