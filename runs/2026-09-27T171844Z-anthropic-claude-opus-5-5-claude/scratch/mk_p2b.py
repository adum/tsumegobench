from build import *
import sys
tree = ("(;W[gb](;B[ga];W[fa]C[RIGHT])(;B[hb];W[fa]C[RIGHT]))"
        "(;W[fa];B[gb])(;W[hb];B[gb])(;W[ga];B[gb])")
t = int(sys.argv[1]) if len(sys.argv) > 1 else 0
sgf, spec = build('e61_17', tree, t)
print(sgf)
errs = check(sgf, spec, maxnodes=60_000_000)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 2 and not errs:
    open(sys.argv[2], 'w').write(sgf)
    print('written', sys.argv[2])
