from build import *
import sys
right = ("(;W[gb]"
         "(;B[ca];W[da](;B[db];W[eb];B[ea](;W[db]C[RIGHT])(;W[ga]C[RIGHT]))"
         "(;B[ea];W[db];B[ga](;W[eb](;B[ha];W[hb](;B[fa];W[ga]C[RIGHT])(;B[ga];W[fa]C[RIGHT]))(;B[hb];W[ha]C[RIGHT]))(;W[ha]C[RIGHT])))"
         "(;B[da];W[eb](;B[ca];W[ea]C[RIGHT])(;B[ea];W[ca];B[ga](;W[db](;B[ha];W[hb]C[RIGHT])(;B[hb];W[ha]C[RIGHT]))(;W[ha]C[RIGHT]))))")
wrong = ("(;W[ca];B[da]C[Seki])(;W[da];B[gb]C[Seki])(;W[eb];B[ea]C[Seki])"
         "(;W[ea];B[eb]C[Ko])(;W[ga];B[ca]C[Ko])(;W[hb];B[ca]C[Ko])")
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('wc8', right + wrong, t, shift=sh)
print(sgf)
errs = check(sgf, spec, verbose=False)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
