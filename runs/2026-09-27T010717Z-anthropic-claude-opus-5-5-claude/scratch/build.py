import sys
from probs import *
def build(name, tree, out=None, verbose=True):
    sp = P[name]
    txt = mk(sorted(sp.AB), sorted(sp.AW), tree)
    root = parse_sgf(txt)
    issues = verify(sp, root, verbose=verbose)
    if out:
        open(out, 'w').write(txt)
    return txt, issues
if __name__ == '__main__':
    name = sys.argv[1]; tree = open(sys.argv[2]).read().strip()
    out = sys.argv[3] if len(sys.argv) > 3 else None
    txt, issues = build(name, tree, out)
    print(txt)
