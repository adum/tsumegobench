from build import *
d=[
". O . X X O ,",
"O . O . X O ,",
"X . . . X O ,",
"X X . X X O ,",
"X X X X O , ,",
"O O O O , , ,",
]
c=Ctx(d,2,2,['ed'],(0,0,6,5))
ch=auto(c,maxrep=2,maxwrong=8);print(dsl(ch),stats(ch))
t=dsl(ch)
ch=report(c,t)
print(write('../outputs/problem-03.sgf',c,ch,k=3))
