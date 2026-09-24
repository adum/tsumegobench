from build import *
d=[
", O . . . X . X O ,",
", O . . . O . . O ,",
", O X X X X X X O ,",
", , O O O O O O , ,",
]
c=Ctx(d,1,2,['cc'],(0,0,9,3))
c.analyze([])
c.analyze(['hb'])
for m in ['ca','da','ea','ga','gb']:c.analyze(['hb',m])
ch=auto(c,maxrep=4,maxwrong=9);print(dsl(ch),stats(ch))
