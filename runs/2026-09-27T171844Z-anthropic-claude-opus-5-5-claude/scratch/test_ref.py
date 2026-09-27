from gotools import *
import time

# gp-5844: Black to kill.
root = parse_sgf(open('../inputs/examples/gp-5844.sgf').read())
b = board_from_sgf_root(root)
region = [sgf2i(s) for s in ['dp', 'ep', 'fp', 'dq', 'dr', 'ds']]
safe = [i for i in range(361) if b.b[i] == BLACK]
target = [i for i in range(361) if b.b[i] == WHITE]
prob = Problem(b, region, safe, target, BLACK)
t = time.time()
print(classify(prob, b, BLACK, BLACK, 'kill'))
print(time.time() - t)

# gp-53750: White to live.
root = parse_sgf(open('../inputs/examples/gp-53750.sgf').read())
b = board_from_sgf_root(root)
print(b.show(2, 14, 13, 18))
pts = ['gr', 'gs', 'hs', 'ir', 'js', 'ks', 'gq', 'iq', 'kq', 'lq', 'es', 'fs', 'ir']
region = [sgf2i(s) for s in ['gr', 'gs', 'hs', 'ir', 'js', 'ks', 'gq', 'iq', 'kq', 'lq', 'es']]
safe = [i for i in range(361) if b.b[i] == BLACK and i2sgf(i) not in ('gs', 'ms', 'mr')]
target = [sgf2i(s) for s in ['jr', 'kr', 'lr']]
prob = Problem(b, region, safe, target, BLACK)
t = time.time()
print(classify(prob, b, WHITE, WHITE, 'live'))
print(time.time() - t)
