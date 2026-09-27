from build import *
import sys
right = "(;W[ab](;B[aa](;W[ca]C[RIGHT])(;W[cb];B[ca];W[bb]C[RIGHT]))(;B[cb];W[ca]C[RIGHT]))"
wrong = "(;W[aa];B[ab])(;W[ca];B[cb])(;W[cb];B[ab])"
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('c31_6', right + wrong, t, shift=sh)
print(sgf)
errs = check(sgf, spec)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
