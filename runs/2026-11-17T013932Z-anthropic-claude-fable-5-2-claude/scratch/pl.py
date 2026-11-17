import sys, json; sys.path.insert(0,'scratch')
from build import *
pool={d['src']:d for d in json.load(open('scratch/out/pool.json'))}
def pline(n):
    best=[]
    for c in n.children:
        l=[c.move]+pline(c)
        if len(l)>len(best): best=l
    return best
for src in sys.argv[1:]:
    d=pool[src]
    p=Problem(d['diag'], defender='W', first=d['first'], maxnodes=3000000)
    b=B2(p, wrong_root=[], inner={}, inner_wrong=0, max_right_len=11); root=b.build()
    print('==', src, d['first'], 'nodes', count_nodes(root))
    print(p.show(h=len(d['diag'].split('\n')))) if False else print('\n'.join(' '.join(r) for r in d['diag'].split('\n')))
    print('ROOT', p.report())
    print('PV:', ' '.join(pline(root)))
    # refutations of wrong first moves
    st,v=p.query([])
    outs=[]
    for m in sorted(v):
        if m=='pass' or v[m]>=2: continue
        st2,v2=p.query([m])
        refs=sorted(r for r,x in v2.items() if x<2 and r!='pass')
        outs.append('%s->%s'%(m,'/'.join(refs)))
    print('REF:', '  '.join(outs))
    p.close()
