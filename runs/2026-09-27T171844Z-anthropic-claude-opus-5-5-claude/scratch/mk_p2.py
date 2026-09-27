from build import *
import sys
tree = "(;W[ea]C[RIGHT])(;W[ha];B[ea]C[Ko])(;W[da];B[ea]C[Ko])(;W[fa];B[ea]C[Ko])"
t = int(sys.argv[1]) if len(sys.argv) > 1 else 5
sgf, spec = build('p2e', tree, t)
print(sgf)
errs = check(sgf, spec)
print('ERRORS' if errs else 'OK')
if len(sys.argv) > 2 and not errs:
    open(sys.argv[2], 'w').write(sgf)
    print('written', sys.argv[2])
