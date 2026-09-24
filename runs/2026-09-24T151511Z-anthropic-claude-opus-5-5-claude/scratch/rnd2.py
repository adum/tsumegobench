from rnd import *
import build
LIMIT=[30000]
def busy(b,p):
    x,y=p%N,p//N;c=0;cols=set();edge=min(x,y)
    for dx in range(-2,3):
        for dy in range(-2,3):
            xx,yy=x+dx,y+dy
            if 0<=xx<N and 0<=yy<N and b[yy*N+xx]:c+=1;cols.add(b[yy*N+xx])
    return c,len(cols),edge
def rrun2(frame,tomove,attacker,keys,box,n=3000,seed=0,w={'.':0.55,'X':0.25,'O':0.2},mind=5,maxnodes=70,show_n=30,minbusy=7,minml=0):
    R=random.Random(seed)
    rows=[r.replace(' ','') for r in frame]
    q=[(x,y) for y,r in enumerate(rows) for x,ch in enumerate(r) if ch=='?']
    outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
    seen=set();found=0
    for it in range(n):
        rr=[list(r) for r in rows]
        for x,y in q:rr[y][x]=R.choices(list(w),weights=list(w.values()))[0]
        key=''.join(''.join(r) for r in rr)
        if key in seen:continue
        seen.add(key)
        b=parse([''.join(r) for r in rr])
        if not legal(b):continue
        if any(b[P(k)]!=3-attacker for k in keys):continue
        try:
            r=evalpos(b,tomove,attacker,keys,box,outs)
        except TimeoutError:continue
        if not r:continue
        s,wins,res=r
        if len(wins)!=1:continue
        c,nc,edge=busy(b,P(wins[0]))
        if c<minbusy or nc<2 or edge<1:continue
        ctx=build.Ctx.__new__(build.Ctx);ctx.b=b;ctx.tomove=tomove;ctx.att=attacker;ctx.cs=s;ctx.box=box
        d=0
        if tomove==attacker and mind>1:
          try:d=s.dist(play(b,P(wins[0]),tomove)[0],3-tomove)
          except TimeoutError:continue
          if d is None or d+1<mind:continue
        try:
            ch=build.auto(ctx,maxrep=2)
        except TimeoutError:continue
        nn,ml=build.stats(ch)
        if nn>maxnodes or ml>14 or ml<minml:continue
        # fresh re-verify without limit
        import cl as _cl
        _cl.set_limit(3000000)
        try:
            r2=evalpos(b,tomove,attacker,keys,box,outs)
        except TimeoutError:
            r2=None
        finally:
            _cl.set_limit(LIMIT[0])
        if not r2 or r2[1]!=wins:
            print('REJECT-reverify',wins,r2 and r2[1]);continue
        ctx=build.Ctx.__new__(build.Ctx);ctx.b=b;ctx.tomove=tomove;ctx.att=attacker;ctx.cs=r2[0];ctx.box=box
        ch=build.auto(ctx,maxrep=2)
        nn,ml=build.stats(ch)
        import kochk
        if kochk.ko_in_tree(ctx,ch):print('REJECT-ko');continue
        nwrong=sum(1 for v in res.values() if v!=(tomove==attacker))
        print('FOUND depth',d+1,'wins',wins,'nodes',nn,ml,'busy',c,'wrong',nwrong)
        show(b,(box[0],box[1],box[2]+1,box[3]+1))
        print('TREE',build.dsl(ch));sys.stdout.flush()
        found+=1
        if found>=show_n:break
FR={
'H1':([   # black corner group, white outside
"? ? ? ? ? X O ,",
"? ? ? ? ? X O ,",
"? ? ? ? X O , ,",
"? ? ? X X O , ,",
"? ? X O O , , ,",
"X X O , , , , ,",
"O O O , , , , ,",
],['ed'],2),
'H2':([   # white corner group, black outside
"? ? ? ? ? O X ,",
"? ? ? ? O O X ,",
"? ? ? ? O X , ,",
"? ? ? O X X , ,",
"? O O X , , , ,",
"O X X , , , , ,",
"X X , , , , , ,",
],['ec'],1),
'H3':([   # black corner, wider
"? ? ? ? ? ? X O ,",
"? ? ? ? ? ? X O ,",
"? ? ? ? X X O , ,",
"? ? X X O O , , ,",
"X X O O , , , , ,",
"O O , , , , , , ,",
],['ec'],2),
'H4':([   # white corner, wider on left side
"? ? ? ? O X ,",
"? ? ? ? O X ,",
"? ? ? O X , ,",
"? ? ? O X , ,",
"? ? O X , , ,",
"? ? O X , , ,",
"O O X , , , ,",
"X X X , , , ,",
],['dc'],1),
}
if __name__=='__main__':
    import cl;cl.set_limit(300000)
    name=sys.argv[1];tm=int(sys.argv[2]);seed=int(sys.argv[3])
    fr,keys,att=FR[name]
    box=(0,0,len(fr[0].split())-1,len(fr)-1)
    rrun2(fr,tm,att,keys,box,n=int(sys.argv[5]),seed=seed,mind=int(sys.argv[4]))
