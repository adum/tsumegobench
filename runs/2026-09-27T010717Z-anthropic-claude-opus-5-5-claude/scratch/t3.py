from tl import *
import time
root = parse_sgf(open('../inputs/examples/gp-18843.sgf').read())
for reg in ['aa:dc', 'aa:ee']:
    sp = spec_from_root(root, reg, 'B', 'live', 'bc')
    bd = sp.board()
    t=time.time(); print(run(sp, bd, BLACK), time.time()-t)
