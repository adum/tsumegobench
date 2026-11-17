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
    p=Problem(d['diag'], defender='W', first=d['first'], maxnodes=5000000)
    try:
        b=B2(p, K=1, wrong_root=[], inner={}, inner_wrong=0, max_right_len=13); root=b.build()
        b2=B2(p, K=1); full=b2.build()
        print(src, d['first'], d['key'], 'K1 right nodes', count_nodes(root), 'depth', max_depth(root), 'full', count_nodes(full), 'PV', ' '.join(pline(root)), '| kos', len(d['kos']), 'traps', d['traps'], 'moves', d['nmoves'])
    except Exception as e:
        print(src, 'ERR', str(e)[:80])
    p.close()
