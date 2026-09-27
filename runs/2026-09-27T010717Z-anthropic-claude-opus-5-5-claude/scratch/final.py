import sys
from probs import *
def finalize(name, treefile, T, out, verbose=False):
    sp = tspec(P[name], T)
    tree = ttree(open(treefile).read().strip(), T)
    txt = mk(sorted(sp.AB), sorted(sp.AW), tree)
    root = parse_sgf(txt)
    issues = verify(sp, root, verbose=verbose)
    for i in issues: print('ISSUE', i)
    open(out, 'w').write(txt)
    print(show(sp.board(), set(sp.region)))
    print(txt)
if __name__ == '__main__':
    finalize(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
