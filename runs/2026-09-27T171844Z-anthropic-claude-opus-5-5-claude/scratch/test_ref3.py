from gotools import *
import time
root = parse_sgf(open('../inputs/examples/gp-1311.sgf').read())
b = board_from_sgf_root(root)
pts = ['aa','ba','ca','da','ea','fa','ga','ha','ab','gb','cb','db','ac','fc','hc','ad','fd','gd','ae']
region = [sgf2i(s) for s in pts]
safe = [sgf2i(s) for s in ['cg', 'ge', 'ie', 'ic', 'hb', 'hd', 'bd', 'cd', 'dd', 'ed', 'ec']]
target = [sgf2i(s) for s in ['bb', 'bc', 'cc', 'dc', 'eb', 'fb']]
prob = Problem(b, region, safe, target, BLACK)
print(len(region))
t = time.time()
print(classify(prob, b, BLACK, BLACK, 'kill', maxnodes=100_000_000))
print(time.time() - t)
