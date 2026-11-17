import sys; sys.path.insert(0,'scratch')
from tsu import *
from cands import C
FINAL=['e46','k83','m4','cut2','bb5ko','c15','peep22','s23','c12','c84']
for name in (sys.argv[1:] or FINAL):
    s=C[name]; diag=s['diag'].replace('/','\n')
    p=Problem(diag, defender='W', first=s['first'])
    g=p.board(); reg=set(p.regboth)
    bad=[]
    for q in p.white:
        for n in neighbours(q):
            if n not in g and n not in reg: bad.append((q,n))
    # region empties adjacent to non-region empties (leaks)
    leaks=[]
    for q in reg:
        if q in g: continue
        for n in neighbours(q):
            if n not in g and n not in reg: leaks.append((q,n))
    # wall groups: outside liberties
    seen=set(); weak=[]
    for q in p.black:
        if q in seen or q in reg: continue
        grp,libs=group(g,q); seen|=grp
        out=[l for l in libs if l not in reg]
        if len(out)<2: weak.append((sorted(grp)[0],len(grp),len(out)))
    print(name, 'white-libs-outside-region:', bad, 'leaks:', leaks, 'weak walls:', weak, 'stones', len(p.black)+len(p.white), 'region empties', len([q for q in reg if q not in g]))
