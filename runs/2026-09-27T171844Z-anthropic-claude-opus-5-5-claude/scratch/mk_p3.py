from build import *
right = ("(;W[db]"
         "(;B[ba];W[ca];B[ab];W[aa]C[RIGHT])"
         "(;B[ab](;W[aa];B[ba];W[ca]C[RIGHT])(;W[ba]C[RIGHT])(;W[ca];B[ba];W[aa]C[RIGHT]))"
         "(;B[ca](;W[ba]C[RIGHT])(;W[aa];B[ba];W[cb];B[ba];W[ca]C[RIGHT])"
         "(;W[cb](;B[aa];W[ba]C[RIGHT])(;B[ab](;W[aa]C[RIGHT])(;W[ba]C[RIGHT]))(;B[ba];W[aa];B[ba];W[ca]C[RIGHT]))))")
wrong = ("(;W[ba];B[db])"
         "(;W[cb];B[db](;W[aa];B[ca])(;W[ca];B[aa]))"
         "(;W[ca];B[db](;W[aa];B[cb])(;W[cb];B[aa]))"
         "(;W[aa];B[db](;W[ca];B[cb])(;W[cb];B[ca]))"
         "(;W[ab];B[db])")
import sys
t = int(sys.argv[1]) if len(sys.argv) > 1 else 3
sgf, spec = build('m12_3', right + wrong, t)
print(sgf)
errs = check(sgf, spec)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 2 and not errs:
    open(sys.argv[2], 'w').write(sgf)
    print('written', sys.argv[2])
