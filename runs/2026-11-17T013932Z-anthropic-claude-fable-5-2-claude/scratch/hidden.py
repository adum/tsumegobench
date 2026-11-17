"""For each RIGHT leaf, count only-moves still required later under best play (hidden forced depth)."""
import sys; sys.path.insert(0,'scratch')
from build import *
from cands import C
sys.setrecursionlimit(10000)

def analyse(name, cap=8):
    s=C[name]; diag=s['diag'].replace('/','\n')
    p=Problem(diag, defender='W', first=s['first'], maxnodes=10000000)
    root=parse_tree(s['tree']) if 'tree' in s else B2(p, **s.get('kw',{})).build()
    memo={}
    def T(moves, d):
        # solver has just moved. returns (count of only-moves required later, example line)
        key=('T',moves)
        if key in memo: return memo[key]
        if d>=cap: return (0,())
        st,v=p.query(list(moves))
        if st: return (0,())
        best=(0,())
        for r in sorted(v):
            if r=='pass': continue
            st2,v2=p.query(list(moves+(r,)))
            if st2: continue
            if v2.get('pass',0)>=2: continue
            wins=[m for m,x in v2.items() if x>=2 and m!='pass']
            if not wins: continue
            cand=None
            for a in wins:
                t=T(moves+(r,a), d+2)
                val=(1 if len(wins)==1 else 0)+t[0]
                if cand is None or val<cand[0]: cand=(val,(r,a+('!' if len(wins)==1 else ''))+t[1])
            if cand[0]>best[0]: best=cand
        memo[key]=best
        return best
    out=[]
    def walk(n, moves):
        for c in n.children:
            mm=moves+(c.move,)
            if c.right:
                t=T(mm,0)
                out.append((t[0], ' '.join(mm), ' '.join(t[1])))
            walk(c, mm)
    walk(root, ())
    p.close()
    print('==', name)
    for h,line,ex in sorted(out, reverse=True):
        if h>0: print('  hidden=%d  leaf: %s   e.g. %s'%(h,line,ex))
    print('  leaves:', len(out), 'max hidden', max(h for h,_,_ in out))

if __name__=='__main__':
    for n in sys.argv[1:]: analyse(n)
