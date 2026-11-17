import sys, os; sys.path.insert(0,'scratch')
from tsu import *
from cands import C
name=sys.argv[1]
s=C[name]; diag=s['diag'].replace('/','\n')
p=Problem(diag, defender='W', first=s['first'], maxnodes=20000000)
def dump(moves, depth):
    st,v=p.query(list(moves))
    print(' '.join(moves) or 'root', st or sorted(v.items()))
    if depth>0 and not st:
        for m in sorted(v):
            if m!='pass': dump(moves+(m,), depth-1)
dump(tuple(sys.argv[2].split(',')), int(sys.argv[3]))
p.close()
