from kochk import *
d=[
". . X X . O X ,",
". . O X O O X ,",
"O O . X O O X ,",
"O O O O O X , ,",
"X X X X X , , ,",
]
c=Ctx(d,2,1,['ed'],(0,0,7,4))
for r in depth_consistency(c):print(r)
