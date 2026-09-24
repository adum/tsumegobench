from build import *
d=[
", X . O O X X O X ,",
", X . . O . . O X ,",
", X O O O O O O X ,",
", , X X X X X X , ,",
]
c=Ctx(d,2,1,['cc'],(0,0,9,3))
c.analyze([])
c.analyze(['cb'])
ch=auto(c,maxrep=3,maxwrong=9);print(dsl(ch),stats(ch))
ch=report(c,"(cb (fb gb R)(gb fb R))(ca cb)(db ca)(fb cb)(gb cb)")
print(write('../outputs/problem-02.sgf',c,ch,k=6))
