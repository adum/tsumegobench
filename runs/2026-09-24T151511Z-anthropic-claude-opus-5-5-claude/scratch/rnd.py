from find2 import *
import build,sys,random
def rrun(frame,tomove,attacker,keys,box,n=3000,seed=0,w={'.':0.6,'X':0.2,'O':0.2},mind=5,maxnodes=60,maxwin=1,show_n=20):
    R=random.Random(seed)
    rows=[r.replace(' ','') for r in frame]
    q=[(x,y) for y,r in enumerate(rows) for x,ch in enumerate(r) if ch=='?']
    outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
    seen=set();found=0
    for it in range(n):
        rr=[list(r) for r in rows]
        for x,y in q:
            rr[y][x]=R.choices(list(w),weights=list(w.values()))[0]
        key=''.join(''.join(r) for r in rr)
        if key in seen:continue
        seen.add(key)
        b=parse([''.join(r) for r in rr])
        if not legal(b):continue
        if any(b[P(k)]!=3-attacker for k in keys):continue
        # realism: no isolated single stones of defender inside not touching friend? allow
        r=evalpos(b,tomove,attacker,keys,box,outs)
        if not r:continue
        s,wins,res=r
        if not(1<=len(wins)<=maxwin):continue
        ctx=build.Ctx.__new__(build.Ctx);ctx.b=b;ctx.tomove=tomove;ctx.att=attacker;ctx.cs=s;ctx.box=box
        if tomove==attacker:
            d=s.dist(play(b,P(wins[0]),tomove)[0],3-tomove)
            if d is None or d+1<mind:continue
        else:
            d=0
        ch=build.auto(ctx,maxrep=2)
        nn,ml=build.stats(ch)
        if nn>maxnodes or ml>14:continue
        # count solver-bad first moves that are plausible
        print('FOUND depth',(d or 0)+1,'wins',wins,'nodes',nn,ml)
        show(b,(box[0],box[1],box[2]+1,box[3]+1))
        print('TREE',build.dsl(ch));sys.stdout.flush()
        found+=1
        if found>=show_n:break
