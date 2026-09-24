from build import *
d=[
", X . X . . . O X ,",
", X O X O O O O X ,",
", X O O O O O X X ,",
", , X X X X X , , ,",
]
c=Ctx(d,2,1,['cb'],(0,0,9,3))
c.analyze([])
ch=auto(c);print(dsl(ch),stats(ch))
t="(ca (ea fa R)(fa ea R))(ea ca)(fa ca)(ga ca)"
ch=report(c,t)
print(write('../outputs/problem-01.sgf',c,ch,k=2))
