import sys, io, contextlib
from probs import *
from registry import REG
for nn, (name, tf, T) in sorted(REG.items()):
    sp = tspec(P[name], T)
    root = parse_sgf(open(f'../outputs/problem-{nn}.sgf').read())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        issues = verify(sp, root, verbose=True)
    lines = buf.getvalue().split('\n')
    leaves = [l for l in lines if l.strip().startswith('leaf')]
    wr = [l for l in leaves if 'leaf wrong' in l]
    rt = [l for l in leaves if 'leaf RIGHT' in l]
    kinds = {}
    for l in wr:
        k = l.split('[')[1].split(']')[0]
        kinds[k] = kinds.get(k, 0) + 1
    nodes = [l for l in lines if l.startswith('nodes')]
    issues = [i for i in issues if not i.endswith("['pass']") and 'wrong leaf ends on solver move' not in i]
    print(nn, name, 'RIGHT leaves', len(rt), 'wrong leaves', kinds, nodes, 'issues', issues)
