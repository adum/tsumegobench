from build import *
d=[
", O . . . . . . O ,",
", O . X X . X X O ,",
", O X X . X X O , ,",
", , O O O O O O , ,",
", , , , , , , , , ,",
]
c=Ctx(d,1,2,['db'],(0,0,9,4))
ch=auto(c)
print(dsl(ch));print(stats(ch))
for e in c.check_tree(ch):print(e)
