from find2 import *
import sys
FR={
# black corner, white kills (att=2)
'A':([
". . . ? ? O ,",
". ? . X X O ,",
"? . X ? O , ,",
"? X ? O , , ,",
"? X O , , , ,",
". X O , , , ,",
"? O , , , , ,",
], ['db'],2),
'B':([
". . ? . ? X O ,",
". ? X X . X O ,",
". . X ? X O O ,",
"? X O O O , , ,",
". X O , , , , ,",
"? ? O , , , , ,",
], ['cc'],2),
'C':([
". . . ? . ? O ,",
"? . X X X X O ,",
". X ? O O O , ,",
"? X O , , , , ,",
". X O , , , , ,",
"? O , , , , , ,",
], ['cb'],2),
'D':([
", O ? . . . ? O ,",
", O X ? X X X O ,",
", O X O ? ? O , ,",
", O X O , , , , ,",
", , O , , , , , ,",
], ['eb'],2),
'E':([
", X . ? . ? . . X ,",
", X O O ? O ? O X ,",
", X X O O O O X X ,",
", , , X X X X , , ,",
], ['db'],1),
'F':([
". . ? . O X ,",
". ? . O ? X ,",
"? O O ? X , ,",
". O X X , , ,",
"? O X , , , ,",
"O X X , , , ,",
"? X , , , , ,",
], ['dc'.replace('dc','bc')],1),
}
name=sys.argv[1];tm=int(sys.argv[2]);mind=int(sys.argv[3])
fr,keys,att=FR[name]
box=(0,0,len(fr[0].split())-1,len(fr)-1)
run(fr,tm,att,keys,box,mind=mind,maxwin=2,show_n=30,maxnodes=70)
