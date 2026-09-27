from gotools import *
from design import load
d, prob = load('wj30')
b = prob.board.copy()
for m, c in [('bb', BLACK), ('ab', WHITE), ('db', BLACK)]:
    b.play(sgf2i(m), c)
print(b.show(0, 0, 5, 4)); print('ko', b.ko)
for kw in (WHITE, BLACK):
    r, mv, st = prob.solve(b, WHITE, kw, 0)
    print('W to move, kowin', kw, 'r', r, mv, st)
b2 = b.copy(); caps = b2.play(sgf2i('ba'), WHITE)
print('after W ba caps', [i2sgf(x) for x in caps], 'ko', i2sgf(b2.ko) if b2.ko is not None else None)
print(b2.show(0, 0, 5, 4))
for kw in (WHITE, BLACK):
    r, mv, st = prob.solve(b2, BLACK, kw, 0)
    print('B to move, kowin', kw, 'r', r, mv, st)
