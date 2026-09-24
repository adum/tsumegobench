from ex2 import *
import cl,sys
cl.set_limit(2000000)
def go(d,tm,att,keys,box):
    try:ex(d,tm,att,keys,box,replies=False)
    except TimeoutError:print('timeout')
d=[
". . X . O , ,",
"X X . X O , ,",
"O X X X O , ,",
". O O O O , ,",
", , , , , , ,",
]
go(d,2,2,['bb'],(0,0,6,4))
d=[
". X . X . O ,",
". O X . X O ,",
"X X X X X O ,",
"O O O O O O ,",
", , , , , , ,",
]
go(d,2,2,['cc'],(0,0,6,4))
go(d,1,2,['cc'],(0,0,6,4))
