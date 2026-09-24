from rnd2 import *
import cl,random
from rnd4 import FR4
cl.set_limit(25000)
fr,keys,att=FR4['K4']
rows=[r.replace(' ','') for r in fr]
q=[(x,y) for y,r in enumerate(rows) for x,ch in enumerate(r) if ch=='?']
outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
R=random.Random(1)
tgt=parse([r.replace(' ','') for r in [". O . . O O X ,",". . . X O O X ,","X . . X O O X ,","O O O O O X , ,","X X X X X , , ,"]])
def T():
    try:return evalpos(tgt,2,1,['ed'],(0,0,7,4),outs)[1]
    except TimeoutError:return 'TO'
print(0,T())
for i in range(1,400):
    rr=[list(r) for r in rows]
    for x,y in q:rr[y][x]=R.choices('.XO',weights=[.5,.25,.25])[0]
    b=parse([''.join(r) for r in rr])
    if not legal(b) or b[P('ed')]!=2:continue
    try:evalpos(b,2,1,['ed'],(0,0,7,4),outs)
    except TimeoutError:pass
    if i%50==0:print(i,T())
cl.set_limit(0)
print('nolimit',T())
