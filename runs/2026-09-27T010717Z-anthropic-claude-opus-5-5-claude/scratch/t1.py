from solver import *
import time
root = parse_sgf(open('../inputs/examples/gp-18843.sgf').read())
bd = root_board(root)
print(show(bd))
# black to live, region top-left
region = [s2i(p) for p in ['aa','ba','ca','ab','bb','cb','ac','cc','dc','ad','bd'] if bd.b[s2i(p)]==0] 
region = [i for i in range(N*N) if i%N<=4 and i//N<=4 and bd.b[i]==0]
S = Solver(bd, region, BLACK, 'live', [s2i('bc')])
t=time.time()
print(S.winning_moves(bd, BLACK), S.nodes, time.time()-t)
