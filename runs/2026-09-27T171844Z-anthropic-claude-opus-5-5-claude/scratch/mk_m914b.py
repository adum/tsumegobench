from build import *
import sys
right = ("(;B[bb]"
         "(;W[ab];B[ba](;W[cb];B[ca](;W[aa];B[cc]C[RIGHT])(;W[cc];B[aa]C[RIGHT]))"
         "(;W[cc](;B[aa](;W[ca];B[cb]C[RIGHT])(;W[cb];B[ca]C[RIGHT]))(;B[cb]C[RIGHT])))"
         "(;W[ba];B[ab];W[cb];B[cc]C[RIGHT]))")
wrong = ("(;B[ab];W[bb];B[ba];W[aa]C[Ko])(;B[ba];W[bb];B[ab];W[aa]C[Ko])"
         "(;B[cc];W[bb])(;B[aa];W[ab])(;B[cb];W[ba])")
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('m91_4', right + wrong, t, shift=sh)
print(sgf, flush=True)
errs = check(sgf, spec, verbose=False)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
