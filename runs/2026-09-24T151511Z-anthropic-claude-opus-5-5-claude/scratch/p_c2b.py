from build import *
d=[
", X . O . . X O X ,",
", X . O . . . O X ,",
", X O O O O O O X ,",
", , X X X X X X , ,",
]
c=Ctx(d,1,1,['cc'],(0,0,9,3))
for m in [['fb','ea','ca','eb'],['fb','ea','ca','gb'],['fb','ea','ca','fa','gb','eb']]:c.analyze(m)
ch=report(c,"(fb (ea ca (cb fa R)(fa gb (eb gb R)(cb eb R))(gb fa R)(eb fa R))(fa ea (eb fa R)(gb fa R)))(ca fa)(ea fb)(fa fb)(cb fa)(eb ca)(gb fa)")
print(write('../outputs/problem-07.sgf',c,ch,k=1))
