from build import *
d=[
". . . O O X ,",
". . X . O X ,",
". . . O O X ,",
"O . O O X , ,",
"O O O X , , ,",
"X X X , , , ,",
]
c=Ctx(d,1,1,['dd'],(0,0,6,5))
c.analyze([])
c.analyze(['bc'])
ch=auto(c);print(dsl(ch),stats(ch))
