from go import *
from build import parse_tree,paths
import sys,time
def ref_check(d,tomove,att,keys,box,tree,limit_s=600):
    rows=[r.replace(' ','') for r in d]
    b0=parse([r.replace(',','.') for r in rows])
    x0,y0,x1,y1=box
    reg=[y*N+x for y in range(y0,y1+1) for x in range(x0,x1+1) if y<len(rows) and x<len(rows[y]) and rows[y][x]!=',']
    s=Solver2(reg,att,[P(k) for k in keys])
    ch=parse_tree(tree,tomove)
    bad=0
    for p in paths(ch):
        b=b0;ko=None;tm=tomove
        for c,m,cm in p:
            b,ko=play(b,P(m),tm,ko);tm=3-tm
        right=bool(p[-1][2] and 'RIGHT' in p[-1][2])
        attwin=s.win2(b,tm,ko,0)
        good=(attwin==(tomove==att))
        if good!=right:
            bad+=1;print('MISMATCH',[x[1] for x in p],'right',right,'good',good)
    print('ref paths checked, mismatches:',bad)
