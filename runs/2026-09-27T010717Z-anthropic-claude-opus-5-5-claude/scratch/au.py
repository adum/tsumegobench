import sys
from probs import *
from auto import *
sp = P[sys.argv[1]]; K = int(sys.argv[2]) if len(sys.argv) > 2 else 3
A = Auto(sp, K)
bd = sp.board()
t = A.build_right(bd, sp.solver, -1, 0, [])
show_tree(t, 0, 'B' if sp.solver == BLACK else 'W')
print('nodes', count(t))
