from kochk import *
d=[
". O . . O O X ,",
". . . X O O X ,",
"X . . X O O X ,",
"O O O O O X , ,",
"X X X X X , , ,",
]
c=Ctx(d,2,1,['ed'],(0,0,7,4))
c.analyze([])
c.analyze(['bc'])
ch=auto(c,maxrep=3,maxwrong=8);print(dsl(ch),stats(ch))
print('ko',ko_in_tree(c,ch))
