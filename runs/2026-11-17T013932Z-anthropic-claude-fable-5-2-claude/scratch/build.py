"""Draft tree builder using 'forcing reply' criteria."""
import sys; sys.path.insert(0,'scratch')
from author import *

class B2:
    def __init__(self, p, best=2, K=2, max_right_len=11, wrong_root=None, skip_root=(), inner_wrong=2,
                 follow=1, follow_cap=3, stop=(), replies=None, refute=None, inner=None, tries=None, maxreplies=4):
        self.p=p; self.best=best; self.K=K; self.max_right_len=max_right_len
        self.wrong_root=wrong_root; self.skip_root=set(skip_root); self.inner_wrong=inner_wrong
        self.follow=follow; self.follow_cap=follow_cap
        self.stop=set(tuple(s.split()) for s in stop)           # right leaves forced
        self.replies={tuple(k.split()):v.split() for k,v in (replies or {}).items()}  # after right move -> opp replies
        self.refute={tuple(k.split()):v for k,v in (refute or {}).items()}            # after wrong move -> reply
        self.inner={tuple(k.split()):v.split() for k,v in (inner or {}).items()}      # solver node path -> wrong moves
        self.tries={tuple(k.split()):v.split() for k,v in (tries or {}).items()}      # after refutation -> solver tries
        self.maxreplies=maxreplies
    def q(self, moves):
        return self.p.query(list(moves))
    def wins(self, moves):
        st,v=self.q(moves)
        if st: return None
        return sorted(m for m,x in v.items() if x>=self.best and m!='pass')
    def forcing_replies(self, moves):
        st,v=self.q(moves)
        out=[]
        for r in sorted(v):
            if r=='pass': continue
            w=self.wins(moves+(r,))
            if w is None: continue
            st2,v2=self.q(moves+(r,))
            if v2.get('pass',0)>=self.best: continue
            if len(w)<=self.K: out.append((len(w),r))
        out.sort()
        return [r for _,r in out]
    def right(self, node, moves):
        st,v=self.q(moves)
        if st=='CAPTURED' or tuple(moves) in self.stop or len(moves)>=self.max_right_len:
            node.right=True; return
        reps=self.replies.get(tuple(moves))
        if reps is None: reps=self.forcing_replies(moves)[:self.maxreplies]
        if not reps:
            node.right=True; return
        for r in reps:
            c=node.add(Node(r)); self.solver(c, moves+(r,), False)
    def solver(self, node, moves, root):
        st,v=self.q(moves)
        wins=self.wins(moves)
        assert wins, ('no win', moves)
        for m in wins:
            c=node.add(Node(m)); self.right(c, moves+(m,))
        key=tuple(moves)
        if root:
            wrong=self.wrong_root if self.wrong_root is not None else [m for m in sorted(v, key=lambda m:(-v[m],m)) if m!='pass' and v[m]<self.best and m not in self.skip_root]
        elif key in self.inner:
            wrong=self.inner[key]
        else:
            # plausible wrong: those with unique refutation or ko
            cand=[]
            for m in sorted(v):
                if m=='pass' or v[m]>=self.best: continue
                st2,v2=self.q(moves+(m,))
                if st2: continue
                refs=[r for r,x in v2.items() if x<self.best]
                cand.append((0 if v[m]==1 else 1, len(refs), m))
            cand.sort()
            wrong=[m for _,_,m in cand[:self.inner_wrong]]
        for m in wrong:
            r0=self.refute.get(tuple(moves+(m,))) or auto_refutation(self.p, moves+(m,), self.best)
            if r0 is None: continue
            c=node.add(Node(m)); self.wrongline(c, moves+(m,), self.follow if root else 0)
    def wrongline(self, node, moves, follow):
        st,v=self.q(moves)
        assert not st, (st, moves)
        r=self.refute.get(tuple(moves)) or auto_refutation(self.p, moves, self.best)
        assert r is not None and v[r]<self.best, ('bad refutation', moves, r)
        c=node.add(Node(r))
        mm=moves+(r,)
        st2,v2=self.q(mm)
        if st2: return
        tries=self.tries.get(tuple(mm))
        if tries is None:
            tries=[]
            if follow>0:
                for m in sorted(v2):
                    if m=='pass': continue
                    st3,v3=self.q(mm+(m,))
                    if st3=='CAPTURED': continue
                    if st3: continue
                    refs=[x for x,y in v3.items() if y<self.best]
                    if v3.get('pass',0)>=self.best and len(refs)<=1:
                        tries.append(m)
                tries=tries[:self.follow_cap]
        for m in tries:
            st3,v3=self.q(mm+(m,))
            if st3: continue
            r3=self.refute.get(tuple(mm+(m,))) or auto_refutation(self.p, mm+(m,), self.best)
            if r3 is None or v3.get(r3,9)>=self.best: continue
            cc=c.add(Node(m)); self.wrongline(cc, mm+(m,), follow-1)
    def build(self):
        root=Node(); self.solver(root, (), True); return root

def draft(p, **kw):
    b=B2(p, **kw); root=b.build()
    issues,notes=verify(p, root)
    print('\n'.join(dump(p, root)))
    for i in issues: print('ISSUE:', i)
    print('nodes=%d maxdepth=%d'%(count_nodes(root), max_depth(root)))
    return root

if __name__=='__main__':
    import json
    src=sys.argv[1]; fn,idx=src.split(':')
    d=json.loads(open('scratch/out/%s.jsonl'%fn).read().split('\n')[int(idx)])
    p=Problem(d['diag'], defender='W', first=d['first'], maxnodes=5000000)
    print(p.show()); print('ROOT', d['first'], p.report())
    draft(p)
