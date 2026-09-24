from ex2 import *
import time
t=time.time()
d=[
". . . . . . O ,",
". . . . X . O ,",
". . X X . O , ,",
". X . O O , , ,",
". X O , , , , ,",
". O , , , , , ,",
", , , , , , , ,",
]
ex(d,2,2,['cc','bd'],(0,0,7,6),replies=False)
print(time.time()-t)
