from kochk import *
d=[
"X . . O O X ,",
". . O O O X ,",
"X . X O O X ,",
". . . O O X ,",
"O O O O X , ,",
"X X X X , , ,",
]
c=Ctx(d,1,1,['ed'],(0,0,6,5))
c.analyze([])
c.analyze(['bb'])
ch=auto(c,maxrep=3,maxwrong=8);print(dsl(ch),stats(ch))
print('ko',ko_in_tree(c,ch))
