from rnd2 import *
import cl
cl.set_limit(25000)
fr=[
". . X X . O X ,",
". . O X O O X ,",
"O O . X O O X ,",
"O O O O O X , ,",
"X X X X X , , ,",
]
rrun2(fr,2,1,['ed'],(0,0,7,4),n=1,minbusy=0,mind=1)
