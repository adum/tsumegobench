from find2 import *
import cl
d=[
". . X X . O X ,",
". . O X O O X ,",
"O O . X O O X ,",
"O O O O O X , ,",
"X X X X X , , ,",
]
rows=[r.replace(' ','') for r in d]
b=parse(rows)
outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
print(evalpos(b,2,1,['ed'],(0,0,7,4),outs)[1:])
cl.set_limit(25000)
try:print(evalpos(b,2,1,['ed'],(0,0,7,4),outs)[1:])
except TimeoutError:print('TO')
