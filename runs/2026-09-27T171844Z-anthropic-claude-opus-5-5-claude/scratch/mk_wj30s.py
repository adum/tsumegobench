from build import *
import sys
right = ("(;B[ba](;W[bb];B[db](;W[aa](;B[ab];W[ac];B[bc]C[RIGHT])(;B[ac];W[da];B[ca];W[ba];B[da]C[RIGHT]))"
         "(;W[ac];B[aa];W[ab](;B[bc]C[RIGHT])(;B[da]C[RIGHT])))(;W[db];B[bb]C[RIGHT]))")
wrong = ("(;B[bb];W[ba]C[Ko])(;B[db];W[ba]C[Ko])(;B[ab];W[ac]C[Ko])"
         "(;B[aa];W[ab])(;B[bc];W[ba])(;B[ac];W[ba])")
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('wj30', right + wrong, t, shift=sh, swap=True)
print(sgf, flush=True)
errs = check(sgf, spec, verbose=False)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
