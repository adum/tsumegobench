from build import *
d=[
", O X . . . . O ,",
", O X X X . X O ,",
", O O O X X X O ,",
", , , O O O O , ,",
", , , , , , , , ,",
]
c=Ctx(d,2,2,['eb'],(0,0,8,4))
c.analyze([])
c.analyze(['fa'])
