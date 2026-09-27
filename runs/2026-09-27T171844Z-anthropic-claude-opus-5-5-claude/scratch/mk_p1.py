from build import *
tree = "(;B[dc]C[RIGHT])(;B[da];W[dc])(;B[ba];W[dc])(;B[aa];W[dc])"
for t in [0]:
    sgf, spec = build('p1a', tree, t)
    print(sgf)
    errs = check(sgf, spec)
    print('ERRORS' if errs else 'OK')
