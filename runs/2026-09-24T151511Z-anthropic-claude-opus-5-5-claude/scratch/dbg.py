from rnd2 import *
import cl,time
cl.set_limit(300000)
fr,keys,att=FR['H1']
rows=[r.replace(' ','') for r in fr]
R=random.Random(5)
q=[(x,y) for y,r in enumerate(rows) for x,ch in enumerate(r) if ch=='?']
outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
box=(0,0,7,6)
st={'illegal':0,'key':0,'eval_none':0,'timeout':0,'ok':0}
t=time.time()
for i in range(200):
    rr=[list(r) for r in rows]
    for x,y in q:rr[y][x]=R.choices('.XO',weights=[.55,.25,.2])[0]
    b=parse([''.join(r) for r in rr])
    if not legal(b):st['illegal']+=1;continue
    if any(b[P(k)]!=3-att for k in keys):st['key']+=1;continue
    try:
        r=evalpos(b,2,att,keys,box,outs)
    except TimeoutError:st['timeout']+=1;continue
    if not r:st['eval_none']+=1;continue
    st['ok']+=1
print(st,time.time()-t)
