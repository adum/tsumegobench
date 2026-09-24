from find2 import *
import sys
FR={
'e1':([
", X . ? . ? . ? X ,",
", X O ? O ? O O X ,",
", X O O O O O X X ,",
", , X X X X X , , ,",
], ['cb'],1),
'e2':([
", X . . ? . ? X ,",
", X ? O . ? O X ,",
", X O O O O O X ,",
", X O X X X X , ,",
", , X , , , , , ,",
], ['dc'],1),
}
name=sys.argv[1];tm=int(sys.argv[2]);mind=int(sys.argv[3])
fr,keys,att=FR[name]
box=(0,0,len(fr[0].split())-1,len(fr)-1)
run(fr,tm,att,keys,box,mind=mind,maxwin=1,show_n=40)
