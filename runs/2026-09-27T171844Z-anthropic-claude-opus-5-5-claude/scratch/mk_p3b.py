from build import *
import sys
right = "(;W[fb](;B[ea];W[ga]C[RIGHT])(;B[ga];W[ea]C[RIGHT]))"
wrong = "(;W[ea];B[fb])(;W[ga];B[fb])(;W[eb];B[fb])(;W[gb];B[fb])"
t = int(sys.argv[1])
sh = (int(sys.argv[2]), int(sys.argv[3]))
sgf, spec = build('m71_4', right + wrong, t, shift=sh)
print(sgf)
errs = check(sgf, spec)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
