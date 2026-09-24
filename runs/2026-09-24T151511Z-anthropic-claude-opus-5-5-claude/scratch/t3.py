from cl import *
from tool import show
import time
d=[
"...X.O.",
"XXXXOO.",
"OOOOO..",
".......",
]
b=parse([r.replace(' ','') for r in d])
t=time.time()
s=CS(b,(0,0,6,3),2,['ab'])
for p,nb_,nk in s.moves(b,2):
    print(S(p),s.win(nb_,1,nk), lib.ld_nodes())
print(time.time()-t)
