from find2 import *
import sys
# white defender corner, black attacker wall
FR={
'w1':([
"? ? ? ? O X ,",
"? ? ? ? O X ,",
"? ? ? O O X ,",
"? ? O O X , ,",
"O O O X , , ,",
"X X X , , , ,",
], ['ee'.replace('ee','dd')],1),
'b1':([
"? ? ? ? ? X O ,",
"? ? ? ? ? X O ,",
"? ? ? ? X X O ,",
"X X X X X O , ,",
"O O O O O , , ,",
], ['ed'],2),
}
name=sys.argv[1];tm=int(sys.argv[2]);mind=int(sys.argv[3]);seed=int(sys.argv[4])
fr,keys,att=FR[name]
box=(0,0,len(fr[0].split())-1,len(fr)-1)
run(fr,tm,att,keys,box,mind=mind,maxwin=1,show_n=30,limit=4000,seed=seed)
