from build import *
d=[
". . X X . O X ,",
". . O X O O X ,",
"O O . X O O X ,",
"O O O O O X , ,",
"X X X X X , , ,",
]
c=Ctx(d,2,1,['ed'],(0,0,7,4))
c.analyze([])
c.analyze(['bb'])
ch=auto(c,maxrep=3,maxwrong=8);print(dsl(ch),stats(ch))
