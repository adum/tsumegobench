import sys
from probs import *
name = sys.argv[1]; mv = sys.argv[2:]
explore(P[name], mv, show_board=True)
