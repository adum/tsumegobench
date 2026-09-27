from gotools import *
from explore import explore
import time
root = parse_sgf(open('../inputs/examples/gp-1311.sgf').read())
b = board_from_sgf_root(root)
pts = ['aa','ba','ca','da','ea','fa','ga','ha','ab','gb','cb','db','ac','fc','hc','ad','fd','gd','ae']
region = [sgf2i(s) for s in pts]
safe = [sgf2i(s) for s in ['cg', 'ge', 'ie', 'ic', 'hb', 'hd', 'bd', 'cd', 'dd', 'ed', 'ec']]
target = [sgf2i(s) for s in ['bb', 'bc', 'cc', 'dc', 'eb', 'fb']]
prob = Problem(b, region, safe, target, BLACK)
b2 = b.copy()
for m, c in [('ac', BLACK)]:
    b2.play(sgf2i(m), c)
for kowin in (WHITE, BLACK):
    t = time.time()
    r, mv, st = prob.solve(b2, WHITE, kowin, 0, maxnodes=3_000_000)
    print(kowin, r, mv, st, time.time() - t, flush=True)
