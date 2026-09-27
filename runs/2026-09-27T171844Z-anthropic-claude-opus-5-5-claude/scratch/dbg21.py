from gotools import *
import minedload
cs = minedload.parse_file('m5_easy_51.txt')
c = [c for c in cs if c['hdr'].startswith('#21 ')][0]
prob = minedload.to_problem(c)
b = prob.board
print('region', sorted(i2sgf(i) for i in prob.region))
print('target', sorted(i2sgf(i) for i in prob.target))
print('safe', sorted(i2sgf(i) for i in prob.safe))
for kowin, strict in [(WHITE, 0), (BLACK, 0)]:
    r, mv, st = prob.solve(b, BLACK, kowin, strict)
    print('root kowin', kowin, 'r', r, 'ka:', mv.get('ka'), st)
b2 = b.copy(); b2.play(sgf2i('ka'), BLACK)
for kowin, strict in [(WHITE, 0), (BLACK, 0)]:
    r, mv, st = prob.solve(b2, WHITE, kowin, strict)
    print('after ka kowin', kowin, 'r', r, mv, st)
b3 = b2.copy(); b3.play(sgf2i('fa'), WHITE)
for kowin, strict in [(WHITE, 0), (BLACK, 0)]:
    r, mv, st = prob.solve(b3, BLACK, kowin, strict)
    print('after ka fa kowin', kowin, 'r', r, mv, st)
print(b3.show(0,0,13,3))
