import sys, json; sys.path.insert(0,'scratch')
from build import *
pool={d['src']:d for d in json.load(open('scratch/out/pool.json'))}
def get(src, maxnodes=5000000):
    d=pool[src]
    return Problem(d['diag'], defender='W', first=d['first'], maxnodes=maxnodes)
if __name__=='__main__':
    p=get(sys.argv[1]); print(p.show()); print('ROOT', p.report())
    kw=eval('dict(%s)'%sys.argv[2]) if len(sys.argv)>2 else {}
    draft(p, **kw)
