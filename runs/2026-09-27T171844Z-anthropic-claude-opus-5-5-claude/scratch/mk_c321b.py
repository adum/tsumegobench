from build import *
import sys
right = ("(;B[bb]"
         "(;W[ab];B[ba];W[bc];B[ba]C[RIGHT])"
         "(;W[ba];B[ab];W[bc];B[ab]C[RIGHT])"
         "(;W[bc](;B[ab];W[ba];B[ab]C[RIGHT])(;B[ba];W[ab];B[ba]C[RIGHT])(;B[db](;W[ab];B[ba]C[RIGHT])(;W[ba];B[ab]C[RIGHT]))))")
wrong = "(;B[ab];W[bb])(;B[ba];W[bb])(;B[bc];W[bb])(;B[db];W[bb])"
t = int(sys.argv[1]) if len(sys.argv) > 1 else 2
sgf, spec = build('c32_1b', right + wrong, t)
print(sgf)
errs = check(sgf, spec)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 2 and not errs:
    open(sys.argv[2], 'w').write(sgf)
    print('written', sys.argv[2])
