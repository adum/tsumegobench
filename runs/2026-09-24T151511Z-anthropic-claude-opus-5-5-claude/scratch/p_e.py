from build import *
d=[
", X . . . . . . X ,",
", X O O . O O O X ,",
", X X O O O O X X ,",
", , , X X X X , , ,",
]
c=Ctx(d,1,1,['db'],(0,0,9,3))
c.analyze([])
c.analyze(['ea'])
for m in ['eb','da','fa','ga','ca','ha']:
    c.analyze(['ea',m])
t="(ea (eb da R)(ca ha R)(ha ca R)(fa da R))(ca ea)(da ea)(fa ea)(ga ca)(ha ea)(eb ea)"
ch=report(c,t)
print(write('../outputs/problem-02.sgf',c,ch,k=4))
