from go import *
from cl import CS
from tool import show
class Node:
    def __init__(s,color,move,comment=None):
        s.color=color;s.move=move;s.children=[];s.comment=comment
def sgf(b,root_children,extra=''):
    ab=[S(p) for p in range(N*N) if b[p]==1];aw=[S(p) for p in range(N*N) if b[p]==2]
    out='(;GM[1]FF[4]CA[UTF-8]SZ[19]'+extra+'AB'+''.join('[%s]'%x for x in ab)+'AW'+''.join('[%s]'%x for x in aw)
    def rec(n):
        s=';%s[%s]'%('BW'[n.color-1],S(n.move))
        if n.comment:s+='C[%s]'%n.comment
        if len(n.children)==1:return s+rec(n.children[0])
        return s+''.join('('+rec(c)+')' for c in n.children)
    if len(root_children)==1:out+=rec(root_children[0])
    else:out+=''.join('('+rec(c)+')' for c in root_children)
    return out+')'
def stats(children):
    cnt=0;mx=0
    def rec(n,d):
        nonlocal cnt,mx
        cnt+=1;mx=max(mx,d)
        for c in n.children:rec(c,d+1)
    for c in children:rec(c,1)
    return cnt,mx
def paths(children,pre=()):
    for c in children:
        p=pre+((c.color,S(c.move),c.comment),)
        if not c.children:yield p
        else:yield from paths(c.children,p)
class Ctx:
    def __init__(s,d,tomove,attacker,keys,box):
        rows=[r.replace(' ','') for r in d]
        s.b=parse(rows)
        s.outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
        s.tomove=tomove;s.att=attacker;s.cs=CS(s.b,box,attacker,keys,s.outs);s.box=box
    def good(s,b,tm,ko):
        """is position good for solver (tm is side to move)"""
        w=s.cs.win(b,tm,ko)
        return w==(s.tomove==s.att)
    def seq(s,moves):
        b=s.b;ko=None;tm=s.tomove
        for m in moves:
            r=play(b,P(m),tm,ko);assert r,('illegal',m)
            b,ko=r;tm=3-tm
        return b,ko,tm
    def analyze(s,moves):
        """print for position after moves: each move for side to move, whether good for solver"""
        b,ko,tm=s.seq(moves)
        show(b,(s.box[0],s.box[1],s.box[2]+1,s.box[3]+1))
        res=[]
        for p,nb_,nk in s.cs.moves(b,tm,ko):
            g=s.good(nb_,3-tm,nk)
            d=s.cs.dist(nb_,3-tm,nk)
            res.append((S(p),'solver-good' if g else 'solver-bad',d))
        print('to move','BW'[tm-1]);
        for r in res:print('  ',r)
        return res
    def check_tree(s,children):
        """verify each path: legality, and RIGHT-ended paths are good for solver, others bad"""
        errs=[]
        for p in paths(children):
            moves=[m for c,m,cm in p]
            try:b,ko,tm=s.seq(moves)
            except AssertionError as e:errs.append(('illegal',moves));continue
            right=bool(p[-1][2] and 'RIGHT' in p[-1][2])
            g=s.good(b,tm,ko)
            if right!=g:errs.append(('mismatch right=%s good=%s'%(right,g),moves))
        return errs
import re
def parse_tree(t,first):
    """mini DSL: tokens are coords, 'R' marks RIGHT on previous move, '(' ')' branches. colors alternate starting with first."""
    toks=re.findall(r'\(|\)|[a-s]{2}|R',t)
    pos=0
    def seq(color):
        nonlocal pos
        nodes=[];cur=None;head=None;c=color
        while pos<len(toks):
            tk=toks[pos]
            if tk=='(':
                # branches
                brs=[]
                while pos<len(toks) and toks[pos]=='(':
                    pos+=1
                    brs.extend(seq(c))
                    assert toks[pos]==')';pos+=1
                if cur is None:return brs
                cur.children=brs;return head
            if tk==')':break
            if tk=='R':cur.comment='RIGHT';pos+=1;continue
            n=Node(c,P(tk));pos+=1;c=3-c
            if cur is None:head=[n]
            else:cur.children=[n]
            cur=n
        return head or []
    return seq(first)
def report(ctx,tree):
    ch=parse_tree(tree,ctx.tomove)
    print('nodes/maxlen',stats(ch))
    for e in ctx.check_tree(ch):print('ERR',e)
    return ch
def tf(p,k):
    x,y=p%N,p//N
    if k&1:x=N-1-x
    if k&2:y=N-1-y
    if k&4:x,y=y,x
    return y*N+x
def tf_board(b,k):
    nb_=[0]*(N*N)
    for p in range(N*N):
        if b[p]:nb_[tf(p,k)]=b[p]
    return tuple(nb_)
def tf_nodes(ch,k):
    out=[]
    for n in ch:
        m=Node(n.color,tf(n.move,k),n.comment);m.children=tf_nodes(n.children,k);out.append(m)
    return out
def write(fn,ctx,ch,k=0):
    s=sgf(tf_board(ctx.b,k),tf_nodes(ch,k))
    open(fn,'w').write(s);return s
def settled(ctx,b,ko,tm):
    """tm = opponent (non-solver) to move. solver already good. check that opponent's any move then another opponent move still fails"""
    cs=ctx.cs
    st=cs.status(b)
    if st!=0:return True
    for p,nb_,nk in cs.moves(b,tm,ko):
        # opponent plays again
        if not ctx.good(nb_,tm,None):return False
    return True
def auto(ctx,moves=(),depth=0,maxrep=3,maxwrong=6,wrong=True,maxd=14):
    b,ko,tm=ctx.seq(list(moves))
    cs=ctx.cs
    solver=(tm==ctx.tomove)
    kids=[]
    if solver:
        cand=[]
        for p,nb_,nk in cs.moves(b,tm,ko):
            g=ctx.good(nb_,3-tm,nk)
            cand.append((p,nb_,nk,g))
        goods=[c for c in cand if c[3]]
        if len(goods)>2 and depth>0:
            # keep fastest
            def dd(c):
                d=cs.dist(c[1],3-tm,c[2]);return d if d is not None else 99
            if ctx.tomove==ctx.att:goods=sorted(goods,key=dd)[:1]
            else:goods=goods[:1]
        for p,nb_,nk,g in goods:
            n=Node(tm,p)
            if settled(ctx,nb_,nk,3-tm) or len(moves)+1>=maxd:
                n.comment='RIGHT'
            else:
                n.children=auto(ctx,tuple(moves)+(S(p),),depth+1,maxrep,maxwrong,False,maxd)
                if not n.children:n.comment='RIGHT'
            kids.append(n)
        if wrong:
            bads=[c for c in cand if not c[3]][:maxwrong]
            for p,nb_,nk,g in bads:
                n=Node(tm,p)
                # refutation
                reps=[(q,nb2,nk2) for q,nb2,nk2 in cs.moves(nb_,3-tm,nk) if not ctx.good(nb2,tm,nk2)]
                if reps:
                    def score(r):
                        q,nb2,nk2=r
                        return -sum(1 for x,nb3,nk3 in cs.moves(nb2,tm,nk2) if ctx.good(nb3,3-tm,nk3))
                    q=max(reps,key=score)[0]
                    n.children=[Node(3-tm,q)]
                kids.append(n)
    else:
        reps=[]
        for p,nb_,nk in cs.moves(b,tm,ko):
            if ctx.good(nb_,3-tm,nk):
                d=cs.dist(nb_,3-tm,nk) if ctx.tomove==ctx.att else None
                reps.append((-(d or 0),p))
        reps.sort()
        for _,p in reps[:maxrep]:
            n=Node(tm,p)
            n.children=auto(ctx,tuple(moves)+(S(p),),depth+1,maxrep,maxwrong,False,maxd)
            kids.append(n)
    return kids
def dsl(ch):
    def rec(n):
        s=S(n.move)+(' R' if n.comment and 'RIGHT' in n.comment else '')
        if len(n.children)==1:return s+' '+rec(n.children[0])
        if n.children:return s+' '+''.join('('+rec(c)+')' for c in n.children)
        return s
    return ''.join('('+rec(c)+')' for c in ch)
def settled(ctx,b,ko,tm):
    cs=ctx.cs
    if cs.status(b)!=0:return True
    for p,nb_,nk in cs.moves(b,tm,ko):
        if ctx.good(nb_,tm,None):continue  # solver can even tenuki
        cnt=0
        for q,nb2,nk2 in cs.moves(nb_,3-tm,nk):
            if ctx.good(nb2,tm,nk2):
                cnt+=1
                if cnt>=2:break
        if cnt<2:return False
    return True
