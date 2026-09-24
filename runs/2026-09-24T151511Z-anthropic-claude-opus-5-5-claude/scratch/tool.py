from go import *
import time
def setup(diag,region_box=None,region=None):
    b=parse(diag)
    return b
def analyze(diag,tomove,attacker,keys,box,maxd=20,extra_excl=()):
    b=parse(diag)
    x0,y0,x1,y1=box
    reg=[y*N+x for y in range(y0,y1+1) for x in range(x0,x1+1) if b[y*N+x]==0 and S(y*N+x) not in extra_excl]
    s=Solver(reg,attacker,[P(k) for k in keys])
    show(b)
    t=time.time()
    res=[]
    for p,nb_,nk in s.moves(b,tomove,None):
        d=s.dist(nb_,3-tomove,nk,maxd)
        res.append((S(p),d))
    print('tomove',tomove,'attacker',attacker)
    good=[m for m,d in res if (d is not None)==(tomove==attacker)]
    print('winning:',good)
    print('all:',res, '%.1fs'%(time.time()-t))
    return s,b
def show(b,box=(0,0,10,8)):
    x0,y0,x1,y1=box
    print('   '+' '.join(chr(97+x) for x in range(x0,x1+1)))
    for y in range(y0,y1+1):
        print(chr(97+y)+'  '+' '.join('.XO'[b[y*N+x]] for x in range(x0,x1+1)))
