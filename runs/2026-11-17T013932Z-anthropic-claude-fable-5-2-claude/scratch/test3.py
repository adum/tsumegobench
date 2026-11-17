import sys, time, random; sys.path.insert(0,'scratch')
from gen import *
rng = random.Random(21)
t=time.time(); n=0; k=0
while n < 30:
    g = normalise(gen_position(rng,'corner'))
    if g is None: continue
    diag = to_diag(g); n+=1
    nreg = sum(1 for ch in diag if ch == '+')
    t1=time.time()
    res = analyse(diag, maxnodes=600000)
    dt=time.time()-t1
    if dt>2: print(diag); print(nreg, res, '%.1fs'%dt)
print('total %.1fs'%(time.time()-t))
