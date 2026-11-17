import sys; sys.path.insert(0,'scratch')
from build import *
def pline(n):
    best=[]
    for c in n.children:
        l=[c.move]+pline(c)
        if len(l)>len(best): best=l
    return best
def test(diag, firsts='BW', show=True, maxnodes=5000000):
    diag=diag.replace('/','\n').replace(' ','')
    for first in firsts:
        p=Problem(diag, defender='W', first=first, maxnodes=maxnodes)
        if show and first==firsts[0]: print(p.show())
        st,v=p.query([])
        wins=[m for m,x in v.items() if x==2 and m!='pass']
        print(first, 'ROOT', p.report())
        if len(wins)>=1 and v.get('pass')!=2:
            b=B2(p, wrong_root=[], inner={}, inner_wrong=0, max_right_len=11); root=b.build()
            print('   PV:', ' '.join(pline(root)), ' rnodes', count_nodes(root))
            outs=[]
            for m in sorted(v):
                if m=='pass' or v[m]>=2: continue
                st2,v2=p.query([m])
                refs=sorted(r for r,x in v2.items() if x<2 and r!='pass')
                outs.append('%s->%s'%(m,'/'.join(refs)))
            print('   REF:', '  '.join(outs))
        p.close()
if __name__=='__main__':
    for d in sys.argv[2:]:
        test(d, sys.argv[1])
