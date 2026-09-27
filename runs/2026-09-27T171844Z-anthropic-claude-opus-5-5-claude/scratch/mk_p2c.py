from build import *
import sys
tree = ("(;B[ea](;W[ga];B[ia]C[RIGHT])(;W[ia];B[ga]C[RIGHT]))"
        "(;B[ga];W[ea])(;B[ha];W[ea])(;B[ia];W[ea])")
t = int(sys.argv[1]) if len(sys.argv) > 1 else 2
sh = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 0)
sgf, spec = build('e61_25', tree, t, shift=sh)
print(sgf)
errs = check(sgf, spec)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 4 and not errs:
    open(sys.argv[4], 'w').write(sgf)
    print('written', sys.argv[4])
