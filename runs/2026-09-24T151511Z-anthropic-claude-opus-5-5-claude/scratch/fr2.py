from find2 import *
import sys
FR={
'k1':([
". . x . O ,",
". x . X O ,",
"x . X X O ,",
". X O O , ,",
"x X O , , ,",
"O O , , , ,",
], ['dc']),
'k2':([
". . . x O ,",
"o . x X O ,",
". x X O O ,",
"x X O , , ,",
". X O , , ,",
"o O , , , ,",
], ['cc']),
'k3':([
". o . . X O ,",
". . x X X O ,",
". x . X O , ,",
"x X X O , , ,",
". X O , , , ,",
"O O , , , , ,",
], ['dc']),
's3':([
", O . . . . . O ,",
", O x . . x X O ,",
", O X x X X O , ,",
", O O O O O , , ,",
", , , , , , , , ,",
], ['ec'] ),
's4':([
", O . . . o . . O ,",
", O . X . . X X O ,",
", O X x X X x O , ,",
", , O O O O O , , ,",
], ['db']),
's5':([
", , O . . . . O , ,",
", O . X . x . X O ,",
", O X o X X X X O ,",
", O X O O O O O , ,",
", , O , , , , , , ,",
], ['db']),
}
name=sys.argv[1];tm=int(sys.argv[2]);mind=int(sys.argv[3])
fr,keys=FR[name]
box=(0,0,len(fr[0].split())-1,len(fr)-1)
run(fr,tm,2,keys,box,mind=mind,maxwin=2,show_n=25)
