import sys, os, hashlib; sys.path.insert(0,'scratch')
from build import *
from cands import C, FINAL
def build(name):
    s=C[name]; diag=s['diag'].replace('/','\n')
    p=Problem(diag, defender='W', first=s['first'], maxnodes=20000000)
    root=parse_tree(s['tree']) if 'tree' in s else B2(p, **s.get('kw',{})).build()
    issues,notes=verify(p, root)
    sgf=to_sgf(p, root)
    st,v=p.query([])
    p.close()
    return hashlib.sha256(sgf.encode()).hexdigest()[:10], len(issues), sorted(v.items())
for slot,name in sorted(FINAL.items()):
    print(slot, name, os.environ.get('TSEED'), build(name)[:2])
