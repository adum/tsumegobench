import sys
from probs import *
from registry import REG
for nn, (name, tf, T) in sorted(REG.items()):
    if len(sys.argv) > 1 and nn not in sys.argv[1:]: continue
    sp = tspec(P[name], T)
    txt = open(f'../outputs/problem-{nn}.sgf').read()
    root = parse_sgf(txt)
    # compare setup
    ok_setup = sorted(root.props['AB']) == sorted(sp.AB) and sorted(root.props['AW']) == sorted(sp.AW)
    issues = verify(sp, root, verbose=False)
    issues = [i for i in issues if not i.endswith("['pass']")]
    print(nn, name, 'setup_ok', ok_setup, 'issues:', issues)
