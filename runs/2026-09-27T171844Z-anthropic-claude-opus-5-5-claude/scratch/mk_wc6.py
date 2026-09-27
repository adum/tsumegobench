from build import *
import sys
right = "(;W[ga](;B[eb];W[gb]C[RIGHT])(;B[gb];W[eb];B[fa](;W[da]C[RIGHT])(;W[ha](;B[da];W[db]C[RIGHT])(;B[db];W[da]C[RIGHT]))))"
wrong = ("(;W[da];B[eb]C[Seki])(;W[eb];B[ga]C[Seki])(;W[fa];B[eb]C[Seki])"
         "(;W[gb];B[ga]C[Seki])(;W[ha];B[da]C[Seki])(;W[db];B[gb]C[Ko])")
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('wc6', right + wrong, t, shift=sh)
print(sgf, flush=True)
errs = check(sgf, spec, verbose=False)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
