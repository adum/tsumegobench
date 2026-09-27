from tl import *
import time
def test(f, region, solver, goal, key):
    root = parse_sgf(open('../inputs/examples/'+f).read())
    sp = spec_from_root(root, region, solver, goal, key)
    print(f); print(show(sp.board(), set(sp.region)))
    t=time.time(); verify(sp, root); print('time', time.time()-t)
test('gp-18843.sgf', 'aa:ee', 'B', 'live', 'bc')
test('gp-16482.sgf', 'ar:es ap:dq', 'W', 'kill', 'cq')
