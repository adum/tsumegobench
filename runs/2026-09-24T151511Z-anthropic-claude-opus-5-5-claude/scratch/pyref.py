from go import *
import time,sys
d=[". O . . O O X ,",". . . X O O X ,","X . . X O O X ,","O O O O O X , ,","X X X X X , , ,"]
rows=[r.replace(' ','').replace(',','.') for r in d]
b=parse(rows)
# fill outside with solid stones to emulate: put extra black wall around? use region only
reg=[y*N+x for y in range(0,5) for x in range(0,8) if b[y*N+x]==0 and d[y].replace(' ','')[x]!=',']
s=Solver2(reg,1,[P('ed')])
for m in sys.argv[1:]:
    t=time.time()
    nb_,nk=play(b,P(m),2)
    print(m,'attacker wins' if s.win2(nb_,1,nk,0) else 'white lives',time.time()-t)
