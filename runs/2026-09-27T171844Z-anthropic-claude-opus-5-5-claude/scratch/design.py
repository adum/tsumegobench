"""Design helper: python3 design.py <name> [moves...]  -- positions defined in designs.py"""
import sys
import time
from gotools import *
from explore import explore
import designs


def load(name):
    d = designs.D[name]
    b, region, safe, target = diagram(d['rows'])
    if d.get('target'):
        target = {sgf2i(s) for s in d['target']}
    att = d['att']
    prob = Problem(b, region, safe, target, att)
    return d, prob


def box_of(prob):
    xs = [i % N for i in range(361) if prob.board.b[i] or i in prob.region]
    ys = [i // N for i in range(361) if prob.board.b[i] or i in prob.region]
    return (max(0, min(xs) - 1), max(0, min(ys) - 1), min(18, max(xs) + 1), min(18, max(ys) + 1))


if __name__ == '__main__':
    name = sys.argv[1]
    seqs = sys.argv[2:]
    d, prob = load(name)
    first = d['first']
    solver = d['solver']
    objective = d['objective']
    box = box_of(prob)
    t = time.time()
    if not seqs:
        seqs = ['']
    for s in seqs:
        mv = [m for m in s.split(',') if m]
        explore(prob, mv, first, objective, solver, box, maxnodes=d.get('maxnodes', 30_000_000))
        print('time %.1fs' % (time.time() - t), flush=True)
