import sys; sys.path.insert(0,'scratch')
from author import *
def look(diag, first, seqs=((),), maxnodes=5000000):
    p = Problem(diag, defender='W', first=first, maxnodes=maxnodes)
    st, v = p.query([])
    print(p.show()); print('ROOT', first, p.report())
    wins=[m for m,x in v.items() if x==2 and m!='pass']
    for s in seqs:
        s = tuple(s) if s else (wins[0],)
        print('--- after', ' '.join(s)); explore(p, s)
    p.close()
if __name__=='__main__':
    import json
    src=sys.argv[1]; fn,idx=src.split(':')
    line=open('scratch/out/%s.jsonl'%fn).read().split('\n')[int(idx)]
    d=json.loads(line)
    seqs=[tuple(a.split(',')) for a in sys.argv[2:]] or ((),)
    look(d['diag'], d['first'], seqs)
