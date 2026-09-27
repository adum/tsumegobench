from build import *
import sys
right = ("(;W[fb]"
         "(;B[fa];W[ga](;B[ia];W[ja]C[RIGHT])(;B[ja];W[ia]C[RIGHT]))"
         "(;B[ga];W[fa](;B[ia];W[ja]C[RIGHT])(;B[ja];W[ia]C[RIGHT]))"
         "(;B[ia];W[ja]C[RIGHT])"
         "(;B[ja];W[ia](;B[fa];W[ga]C[RIGHT])(;B[ga];W[fa]C[RIGHT])))")
wrong = "(;W[fa];B[fb])(;W[ga];B[fb])(;W[ia];B[fb])(;W[ja];B[fb])"
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('m21_8c', right + wrong, t, shift=sh)
print(sgf)
errs = check(sgf, spec)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
