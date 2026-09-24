from go import *
import sys,time
def check(d,tomove,att,keys,box,moves,depth):
    rows=[r.replace(' ','') for r in d]
    b=parse([r.replace(',','.') for r in rows])
    x0,y0,x1,y1=box
    reg=[y*N+x for y in range(y0,y1+1) for x in range(x0,x1+1) if y<len(rows) and x<len(rows[y]) and rows[y][x]!=',']
    s=Solver(reg,att,[P(k) for k in keys])
    ko=None;tm=tomove
    for m in moves:b,ko=play(b,P(m),tm,ko);tm=3-tm
    t=time.time()
    r=s.win(b,tm,ko,0,depth)
    print(moves,'attacker wins within',depth,':',r,'%.1fs'%(time.time()-t));sys.stdout.flush()
P04=([", O . X . X . . O ,",", O X . . . . . O ,",", O X X X X X X O ,",", , O O O O O O , ,"],2,2,['cc'],(0,0,9,3))
for mv in (['eb','hb','ha'],['eb','db','ha']):
    for dp in (12,16,20):
        check(*P04,mv,dp)
