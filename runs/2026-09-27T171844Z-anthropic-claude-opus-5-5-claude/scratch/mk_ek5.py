from build import *
import sys
right = ("(;B[fb](;W[ca];B[ea];W[gb];B[fa]C[RIGHT])"
         "(;W[ea];B[ca](;W[fa];B[gb];W[eb];B[gb]C[RIGHT])(;W[gb];B[fa];W[eb];B[fa]C[RIGHT]))"
         "(;W[fa];B[ea];W[gb];B[fa]C[RIGHT])"
         "(;W[gb];B[fa](;W[ca];B[ea]C[RIGHT])(;W[ea];B[ca];W[eb];B[fa]C[RIGHT])(;W[eb](;B[ca];W[ea];B[fa]C[RIGHT])(;B[ea];W[da];B[fa]C[RIGHT]))))")
wrong = ("(;B[ca];W[fa](;B[ea];W[gb])(;B[fb];W[gb]))"
         "(;B[ea];W[fb](;B[ca];W[da])(;B[da];W[ca]))"
         "(;B[eb];W[ca](;B[ea];W[fb])(;B[fb];W[ea]))"
         "(;B[fa];W[ca])"
         "(;B[gb];W[ca](;B[ea];W[fb]))"
         "(;B[da];W[ca](;B[ea];W[fb])(;B[fb];W[ea]))")
t = int(sys.argv[1]); sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('ek5', right + wrong, t, shift=sh, swap=True)
print(sgf, flush=True)
errs = check(sgf, spec, verbose=True)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
