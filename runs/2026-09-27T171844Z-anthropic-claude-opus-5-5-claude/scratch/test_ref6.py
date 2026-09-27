from gotools import *
import time
root = parse_sgf(open('../inputs/examples/gp-1311.sgf').read())
b = board_from_sgf_root(root)
pts = ['aa','ba','ca','da','ea','fa','ga','ha','ab','gb','cb','db','ac','fc','hc','ad','fd','gd','ae']
region = [sgf2i(s) for s in pts]
safe = [sgf2i(s) for s in ['cg', 'ge', 'ie', 'ic', 'hb', 'hd', 'bd', 'cd', 'dd', 'ed', 'ec']]
target = [sgf2i(s) for s in ['bb', 'bc', 'cc', 'dc', 'eb', 'fb']]
prob = Problem(b, region, safe, target, BLACK)
line = ['ac','ab','ba','ad','da','ea','ca','aa','ca']
b2 = b.copy(); c = BLACK
for k, m in enumerate(line):
    b2.play(sgf2i(m), c); c = opp(c)
    t = time.time()
    r, mv, st = prob.solve(b2, c, BLACK, 0, maxnodes=2_000_000)
    wins = sorted(k2 for k2, v in mv.items() if v == 1)
    print(k, m, 'tomove', CNAME[c], 'r=', r, 'wins:', wins, st, '%.1fs' % (time.time() - t), flush=True)
print(b2.show(0, 0, 9, 6))
