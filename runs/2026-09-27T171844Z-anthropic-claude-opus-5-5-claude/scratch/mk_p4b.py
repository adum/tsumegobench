from build import *
import sys
right = ("(;B[fa](;W[ea];B[eb];W[fb];B[ea]C[RIGHT])(;W[eb];B[ea]C[RIGHT])(;W[fb];B[ea]C[RIGHT]))")
wrong = "(;B[ea];W[fa]C[Ko])(;B[eb];W[fa]C[Ko])(;B[fb];W[fa])(;B[ga];W[fa])(;B[ha];W[fa])"
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('c32_3', right + wrong, t, shift=sh)
print(sgf)
errs = check(sgf, spec)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
