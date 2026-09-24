from rnd2 import *
import cl
cl.set_limit(25000)
fr=[
". O . . O O X ,",
". . . X O O X ,",
"X . . X O O X ,",
"O O O O O X , ,",
"X X X X X , , ,",
]
rows=[r.replace(' ','') for r in fr]
b=parse(rows)
outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
try:print(evalpos(b,2,1,['ed'],(0,0,7,4),outs)[1:])
except TimeoutError:print('TO')
cl.set_limit(0)
print(evalpos(b,2,1,['ed'],(0,0,7,4),outs)[1:])
