import ctypes,os
from go import *
lib=ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)),'libld4.so'))
lib.ld_limit.argtypes=[ctypes.c_long]
def set_limit(n):lib.ld_limit(n)
class CS:
    def __init__(s,b,box,attacker,keys,outs=()):
        s.outs=set(outs)
        s.x0,s.y0,s.x1,s.y1=box;s.w=s.x1-s.x0+3;s.h=s.y1-s.y0+3
        s.att=attacker;s.keys=[P(k) if isinstance(k,str) else k for k in keys]
        s.region=[y*N+x for y in range(s.y0,s.y1+1) for x in range(s.x0,s.x1+1) if b[y*N+x]==0 and y*N+x not in s.outs]
        s.allbox=[y*N+x for y in range(s.y0,s.y1+1) for x in range(s.x0,s.x1+1) if y*N+x not in s.outs]
        kp=(ctypes.c_int*len(s.keys))(*[s.gi(k) for k in s.keys])
        mv=[s.gi(p) for p in s.allbox]
        # order: moves near keys first? keep geometric
        mva=(ctypes.c_int*len(mv))(*mv)
        lib.ld_init(s.grid(b),s.w,s.h,attacker,kp,len(s.keys),mva,len(mv))
    def gi(s,p):
        x,y=p%N,p//N
        return (y-s.y0+1)*s.w+(x-s.x0+1)
    def grid(s,b):
        out=[]
        for gy in range(s.h):
            for gx in range(s.w):
                x=gx-1+s.x0;y=gy-1+s.y0
                if x<0 or y<0 or x>=N or y>=N:out.append('#')
                elif gx==0 or gy==0 or gx==s.w-1 or gy==s.h-1:out.append('+')
                elif y*N+x in s.outs:out.append('+')
                else:out.append('.XO'[b[y*N+x]])
        return ''.join(out).encode()
    def win(s,b,tm,ko=None,depth=60):
        r=lib.ld_query(s.grid(b),tm,s.gi(ko) if ko is not None else -1,depth)
        if r<0:raise TimeoutError('node limit')
        return bool(r)
    def status(s,b):return lib.ld_status(s.grid(b))
    def dist(s,b,tm,ko=None,maxd=30):
        if not s.win(b,tm,ko,maxd):return None
        for d in range(0,maxd+1):
            if s.win(b,tm,ko,d):return d
    def moves(s,b,tm,ko=None):
        out=[]
        for p in s.region:
            if b[p]!=0:continue
            r=play(b,p,tm,ko)
            if r:out.append((p,r[0],r[1]))
        # also box points that became empty (captures)
        for p in s.allbox:
            if p not in s.region and b[p]==0:
                r=play(b,p,tm,ko)
                if r:out.append((p,r[0],r[1]))
        return out
