from build import *
import sys
right = ("(;B[cb](;W[ca](;B[da];W[db](;B[aa]C[RIGHT])(;B[ca];W[aa];B[ca](;W[ba];B[cb]C[RIGHT])(;W[cb];B[ba]C[RIGHT])))"
         "(;B[db](;W[aa];B[da]C[RIGHT])(;W[da];B[aa]C[RIGHT])))(;W[db];B[ca]C[RIGHT]))")
wrong = "(;B[ca];W[cb])(;B[da];W[cb])(;B[db];W[cb])(;B[aa];W[ca](;B[cb];W[db]))"
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('wg15k', right + wrong, t, shift=sh)
print(sgf, flush=True)
errs = check(sgf, spec, verbose=True)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
