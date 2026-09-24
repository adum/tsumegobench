import itertools,sys,time,random
from go import *
from cl import CS
from tool import show
def legal(b):
    seen=set()
    for p in range(N*N):
        if b[p] and p not in seen:
            g,l=group(b,p);seen|=g
            if len(l)<2:return False
    return True
def evalpos(b,tomove,attacker,keys,box,outs=()):
    s=CS(b,box,attacker,keys,outs)
    if s.status(b)!=0:return None
    if s.win(b,3-tomove)!=(tomove!=attacker):return None
    wins=[];res={}
    for p,nb_,nk in s.moves(b,tomove):
        w=s.win(nb_,3-tomove,nk)
        res[S(p)]=w
        if w==(tomove==attacker):wins.append(S(p))
    return s,wins,res
def run(frame,*a,maxnodes=80,**k):
    return run0(frame,*a,maxnodes=maxnodes,**k)
def run0(frame,tomove,attacker,keys,box,mind=1,maxwin=1,limit=None,opts='.XO',seed=0,show_n=10,minwin=1,maxnodes=80):
    outs=[y*N+x for y,r in enumerate(frame) for x,ch in enumerate(r.replace(' ','')) if ch==',']
    rows=[r.replace(' ','') for r in frame]
    q=[(x,y) for y,r in enumerate(rows) for x,ch in enumerate(r) if ch in '?xo']
    dch='XO'[2-attacker];ach='XO'[attacker-1]
    optl=[{'?':opts,'x':'.X','o':'.O'}[rows[y][x]] for x,y in q]
    combos=list(itertools.product(*optl))
    random.Random(seed).shuffle(combos)
    if limit:combos=combos[:limit]
    found=[]
    for c in combos:
        rr=[list(r) for r in rows]
        for (x,y),ch in zip(q,c):rr[y][x]=ch
        b=parse([''.join(r) for r in rr])
        if not legal(b):continue
        if any(b[P(k)]!=3-attacker for k in keys):continue
        r=evalpos(b,tomove,attacker,keys,box,outs)
        if not r:continue
        s,wins,res=r
        if not(minwin<=len(wins)<=maxwin):continue
        if tomove==attacker:
            depth=max(s.dist(play(b,P(w),tomove)[0],3-tomove) for w in wins)+1
        else:
            depth=min(s.dist(play(b,P(m),tomove)[0],3-tomove) or 99 for m in res if m not in wins)
        if depth<mind:continue
        import build
        ctx=build.Ctx.__new__(build.Ctx);ctx.b=b;ctx.tomove=tomove;ctx.att=attacker;ctx.cs=s;ctx.box=box
        try:
            ch=build.auto(ctx,maxrep=2)
        except Exception as e:
            print('autoerr',e);continue
        nn,ml=build.stats(ch)
        if nn>maxnodes or ml>14:continue
        print('TREE',nn,ml,build.dsl(ch))
        found.append((depth,wins,b))
        print('FOUND depth',depth,'wins',wins,''.join(c));show(b,(box[0],box[1],box[2]+1,box[3]+1));sys.stdout.flush()
        if len(found)>=show_n:break
    return found
