# usage: python3 d.py file   (file: line1 = origin solver goal key ; rest = diagram)
import sys
from tl import *
def load(fn):
    lines = open(fn).read().split('\n')
    origin, solver, goal, key = lines[0].split()[:4]
    return dspec('\n'.join(lines[1:]), origin, solver, goal, key)
if __name__ == '__main__':
    sp = load(sys.argv[1])
    moves = sys.argv[2:]
    explore(sp, moves)
    if not moves:
        # also: what if opponent moves first
        s2 = sp.with_(solver='B' if sp.solver == WHITE else 'W')
        s2.goal = 'kill' if sp.goal == 'live' else 'live'
        print('--- opponent first:')
        explore(s2, [], False)
