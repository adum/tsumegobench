from build import *
d=[
". . . X . O O ,",
". . X X X X O ,",
". X O O O O , ,",
". X O , , , , ,",
". X O , , , , ,",
"O O , , , , , ,",
]
c=Ctx(d,2,2,['cb','bd'],(0,0,7,5))
c.analyze([])
c.analyze(['ba'])
ch=auto(c,maxrep=3);print(dsl(ch),stats(ch))
