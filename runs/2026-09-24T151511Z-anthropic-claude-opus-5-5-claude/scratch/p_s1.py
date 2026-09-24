from build import *
d=[
", O . X . X . . O ,",
", O X . . . . . O ,",
", O X X X X X X O ,",
", , O O O O O O , ,",
]
c=Ctx(d,2,2,['cc'],(0,0,9,3))
c.analyze([])
c.analyze(['eb'])
ch=auto(c,maxrep=3,maxwrong=9);print(dsl(ch),stats(ch))
for m in ['hb','ga','fb','db']:c.analyze(['eb',m])
ch=report(c,"(eb (hb ha R)(fb hb R)(db ha R))(ca ha)(ea eb)(ga ha)(ha eb)(db ha)(fb eb)(gb eb)(hb eb)")
print(write('../outputs/problem-04.sgf',c,ch,k=5))
