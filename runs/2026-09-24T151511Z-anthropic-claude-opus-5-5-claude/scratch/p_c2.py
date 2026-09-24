from build import *
d=[
", X . O . . X O X ,",
", X . O . . . O X ,",
", X O O O O O O X ,",
", , X X X X X X , ,",
]
c=Ctx(d,1,1,['cc'],(0,0,9,3))
c.analyze([])
c.analyze(['fb'])
for m in ['ea','fa','eb','gb','ca']:c.analyze(['fb',m])
ch=auto(c,maxrep=2,maxwrong=8);print(dsl(ch),stats(ch))
for m in [['fb','fa','ea','eb'],['fb','fa','ea','gb'],['fb','ea','ca'],['fb','ea','fa']]:c.analyze(m)
