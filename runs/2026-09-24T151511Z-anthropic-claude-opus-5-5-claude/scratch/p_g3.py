from build import *
d=[
", X . O . . . . X ,",
", X O . . . . O X ,",
", X O O O O O O X ,",
", , X X X X X X , ,",
]
c=Ctx(d,1,1,['cb'],(0,0,9,3))
c.analyze([])
c.analyze(['ha'])
c.analyze(['ha','ga'])
c.analyze(['ha','fa'])
ch=auto(c,maxrep=3);print(dsl(ch),stats(ch))
t="(ha (ga fa (gb eb (ca ea R)(ea fb R)(db ca R))(ca gb R)(ea gb R))(fa eb (ga fb R)(fb ga R))(ca fa R)(eb fa R))(ga ha)(fa ha)(ea fa)(eb fb)(ca ea)(db ca)"
ch=report(c,t)
print(write('../outputs/problem-05.sgf',c,ch,k=5))
