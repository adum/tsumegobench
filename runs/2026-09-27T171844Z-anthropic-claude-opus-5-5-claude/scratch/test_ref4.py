from gotools import *
from explore import explore
root = parse_sgf(open('../inputs/examples/gp-1311.sgf').read())
b = board_from_sgf_root(root)
pts = ['aa','ba','ca','da','ea','fa','ga','ha','ab','gb','cb','db','ac','fc','hc','ad','fd','gd','ae']
region = [sgf2i(s) for s in pts]
safe = [sgf2i(s) for s in ['cg', 'ge', 'ie', 'ic', 'hb', 'hd', 'bd', 'cd', 'dd', 'ed', 'ec']]
target = [sgf2i(s) for s in ['bb', 'bc', 'cc', 'dc', 'eb', 'fb']]
prob = Problem(b, region, safe, target, BLACK)
box = (0, 0, 9, 6)
explore(prob, ['ac'], BLACK, 'kill', BLACK, box)
explore(prob, ['ac', 'ab'], BLACK, 'kill', BLACK, box)
explore(prob, ['ac', 'ab', 'ba'], BLACK, 'kill', BLACK, box)
explore(prob, ['ac', 'ab', 'ba', 'ad'], BLACK, 'kill', BLACK, box)
