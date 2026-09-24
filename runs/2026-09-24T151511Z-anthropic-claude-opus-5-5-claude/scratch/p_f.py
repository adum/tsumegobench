from build import *
d=[
". . . . O X ,",
". . . O O X ,",
"O O O X X , ,",
". O X X , , ,",
". O X , , , ,",
"O X X , , , ,",
"X X , , , , ,",
]
c=Ctx(d,1,1,['bc'],(0,0,6,6))
c.analyze([])
c.analyze(['cb'])
ch=auto(c,maxrep=4);print(dsl(ch),stats(ch))
ch=auto(c,maxrep=2);print(dsl(ch),stats(ch))
c.analyze(['ae'])
c.analyze(['ad'])
c.analyze(['cb','ba','da','bb','ae'])
