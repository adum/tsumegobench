from build import *
d=[
". . O . . X O ,",
"O . . O . X O ,",
"X X . X X X O ,",
"X X X X X O , ,",
"O O O O O , , ,",
]
c=Ctx(d,1,2,['ed'],(0,0,7,4))
c.analyze([])
c.analyze(['bb'])
ch=auto(c,maxrep=3,maxwrong=8);print(dsl(ch),stats(ch))
for m in ['cb','cc','ba','eb']:c.analyze(['bb',m])
ch=report(c,"(bb R)(aa bb)(ba bb)(cb bb)(cc bb)(da bb)(eb bb)")
print(write('../outputs/problem-01.sgf',c,ch,k=2))
