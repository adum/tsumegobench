from cl import *
import time
d=[
". . . . . . O ,",
". . . . X . O ,",
". . X X . O , ,",
". X . O O , , ,",
". X O , , , , ,",
". O , , , , , ,",
", , , , , , , ,",
]
rows=[r.replace(' ','') for r in d]
b=parse(rows)
outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
s=CS(b,(0,0,7,6),2,['cc','bd'],outs)
set_limit(200000)
t=time.time()
try:print(s.win(b,1))
except TimeoutError:print('to')
print(time.time()-t, lib.ld_nodes())
