import itertools,sys,time,random
from go import *
from tool import show
def legal(b):
    seen=set()
    for p in range(N*N):
        if b[p] and p not in seen:
            g,l=group(b,p);seen|=g
            if not l:return False
    return True
def run(frame,tomove,attacker,keys,box,mind=1,maxd=16,maxwin=1,limit=None,opts='.XO',seed=0,show_n=10):
    rows=[r.replace(' ','') for r in frame]
    q=[(x,y) for y,r in enumerate(rows) for x,ch in enumerate(r) if ch=='?']
    combos=list(itertools.product(opts,repeat=len(q)))
    random.Random(seed).shuffle(combos)
    if limit:combos=combos[:limit]
    found=[]
    x0,y0,x1,y1=box
    for c in combos:
        rr=[list(r) for r in rows]
        for (x,y),ch in zip(q,c):rr[y][x]=ch
        b=parse([''.join(r) for r in rr])
        if not legal(b):continue
        kk=[P(k) for k in keys]
        if any(b[k]!=3-attacker for k in kk):continue
        reg=[y*N+x for y in range(y0,y1+1) for x in range(x0,x1+1) if b[y*N+x]==0]
        s=Solver2(reg,attacker,kk)
        if s.status(b)!=0:continue
        # pass test
        dp=s.win2(b,3-tomove,None,1)
        if dp!=(tomove!=attacker):continue  # pass must lose
        wins=[];dists={}
        ok=True
        for p,nb_,nk in s.moves(b,tomove,None):
            w=s.win2(nb_,3-tomove,nk,0)
            d=w
            dists[S(p)]=d
            if w==(tomove==attacker):
                wins.append(S(p))
                if len(wins)>maxwin:ok=False;break
        if not ok or not wins:continue
        s2=Solver(reg,attacker,kk)
        if tomove==attacker:
            depth=max(s2.dist(play(b,P(w),tomove)[0],3-tomove,None,maxd) or 99 for w in wins)+1
        else:
            depth=len([v for v in dists.values() if v])
        if depth<mind:continue
        found.append((depth,wins,b,dists))
        print('FOUND depth',depth,'wins',wins,c);show(b,(x0,y0,x1+1,y1+1));sys.stdout.flush()
        if len(found)>=show_n:break
    return found
