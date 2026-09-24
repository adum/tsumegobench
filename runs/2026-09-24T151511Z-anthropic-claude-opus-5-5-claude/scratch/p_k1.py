from build import *
import cl
d=[
". O . X X O ,",
"O . O . X O ,",
"X . . . X O ,",
"X X . X X O ,",
"X X X X O , ,",
"O O O O , , ,",
]
c=Ctx(d,2,2,['ed'],(0,0,6,5))
c.analyze([])
c.analyze(['cc'])
for m in ['bb','bc','db','cd']:c.analyze(['cc',m])
for m in ['aa','ca','db','dc','cd']:c.analyze(['cc','bb','bc',m])
