from gotools import *
import time

root = parse_sgf(open('../inputs/examples/gp-1311.sgf').read())
b = board_from_sgf_root(root)
region = [xy2i(x, y) for x in range(0, 9) for y in range(0, 5) if b.b[xy2i(x, y)] == EMPTY or i2sgf(xy2i(x, y)) in ('cb', 'db')]
safe = [sgf2i(s) for s in ['cg', 'ge', 'ie', 'ic', 'hb', 'hd', 'bd', 'cd', 'dd', 'ed', 'ec']]
target = [sgf2i(s) for s in ['bb', 'bc', 'cc', 'dc', 'eb', 'fb']]
prob = Problem(b, region, safe, target, BLACK)
print(len(region))
t = time.time()
print(classify(prob, b, BLACK, BLACK, 'kill', maxnodes=50_000_000))
print(time.time() - t)
