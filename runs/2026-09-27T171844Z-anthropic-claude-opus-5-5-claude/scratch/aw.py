import sys
from design import load
import autowrong, etree
from gotools import *
name = sys.argv[1]
moves = sys.argv[2].split(',')
d, prob = load(name)
for m in moves:
    r = autowrong.wrong_branch(prob, prob.board, d['solver'], d['objective'], m)
    print(m, r)
