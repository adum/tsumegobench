from find2 import *
import sys
def V(d,tm,att,keys,box):
    rows=[r.replace(' ','') for r in d]
    b=parse(rows)
    outs=[y*N+x for y,r in enumerate(rows) for x,ch in enumerate(r) if ch==',']
    r=evalpos(b,tm,att,keys,box,outs)
    print(r[1] if r else r)
# K2_1 bb (B kills white corner), frame K2 key ed att1
V(["X . . O O X ,",". . O O O X ,","X . X O O X ,",". . . O O X ,","O O O O X , ,","X X X X , , ,"],1,1,['ed'],(0,0,6,5))
# K3_2 db (B lives) frame K3 key ed att2
V([". . . . O X O ,","O . O . O X O ,","X X . X X X O ,","X X X X X O , ,","O O O O O , , ,"],1,2,['ed'],(0,0,7,4))
# K4_1 #3 cb (W lives)
V([". X . X . O X ,",". . . O . O X ,","X X O O O O X ,","O O O O O X , ,","X X X X X , , ,"],2,1,['ed'],(0,0,7,4))
# K4_1 #2 db
V([". X X . X O X ,","O . . . X O X ,","O O X . O O X ,","O O O O O X , ,","X X X X X , , ,"],2,1,['ed'],(0,0,7,4))
# K3_2 #2 bb
V([". X O O . X O ,","X . O . O X O ,",". X X X X X O ,","X X X X X O , ,","O O O O O , , ,"],1,2,['ed'],(0,0,7,4))
