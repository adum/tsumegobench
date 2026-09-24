import random,sys,time
from go import *
def mk(seed,W=7,H=5):
    R=random.Random(seed)
    b=[0]*(N*N)
    # shape: defender boundary profile per column
    # defender occupies cells where y==hcol[x] (a wall line) , attacker at y==hcol[x]+1
    for x in range(W+2):
        pass
    # random walk wall heights
    h=[R.choice([1,2,2,3]) for _ in range(W)]
    for i in range(1,W):
        h[i]=max(1,min(3,h[i-1]+R.choice([-1,0,0,1])))
    wx=W  # defender vertical wall at column wx-? corner group: columns 0..W-1, right wall at x=W
    hw=max(h)+1
    for x in range(W):
        b[h[x]*N+x]=2
        b[(h[x]+1)*N+x]=1
    for y in range(0,hw+1):
        if b[y*N+W]==0:b[y*N+W]=2
        b[y*N+W+1]=1
    for x in range(W+2):
        if b[(hw+1)*N+x]==0 and x>=0:b[(hw+1)*N+x]=1 if any(b[(yy)*N+x]==1 for yy in range(hw+1)) or x>=W else 0
    # connect vertical steps of defender wall
    for x in range(1,W):
        a,c=h[x-1],h[x]
        for y in range(min(a,c),max(a,c)):
            if b[y*N+x]==0 and b[y*N+x-1]!=0: pass
        if a!=c:
            for y in range(min(a,c)+1,max(a,c)+1):
                # fill with defender on the column with smaller h
                xx = x if c<a else x-1
                if b[y*N+xx]==0:b[y*N+xx]=2
    # noise: remove / add stones
    cells=[y*N+x for y in range(hw+2) for x in range(W+1)]
    for _ in range(R.randint(1,4)):
        p=R.choice(cells);b[p]=R.choice([0,0,1,1,2])
    return tuple(b),W,hw
def legal(b):
    seen=set()
    for p in range(N*N):
        if b[p] and p not in seen:
            g,l=group(b,p);seen|=g
            if not l:return False
    return True
