import sys, json, glob; sys.path.insert(0,'scratch')
from build import *
def load(src):
    fn,idx=src.split(':')
    return json.loads(open('scratch/out/%s.jsonl'%fn).read().split('\n')[int(idx)])
def pline(n):
    best=[]
    for c in n.children:
        l=[c.move]+pline(c)
        if len(l)>len(best): best=l
    return best
if __name__=='__main__':
    for src in sys.argv[1:]:
        d=load(src)
        p=Problem(d['diag'], defender='W', first=d['first'], maxnodes=5000000)
        full=B2(p, K=1).build()
        print('==', src, d['first'], 'key', d['key'], 'pv', ' '.join(d['pv']), '| right', d['rnodes'], 'full', count_nodes(full), 'depth', max_depth(full))
        print(d['diag'].replace('\n','/'))
        print('ROOT', p.report())
        p.close()
