from find2 import *
import sys
FR={
# black corner group, white outside
'c1':[
". . . x . o O ,",
". . x . X o O ,",
". x . X X O , ,",
"x . X O O , , ,",
". X O , , , , ,",
"o X O , , , , ,",
"O O , , , , , ,",
],
'c2':[
". . . . x . O ,",
". x . x X o O ,",
". . X X O O , ,",
"x X O O , , , ,",
". X O , , , , ,",
"o o O , , , , ,",
", , , , , , , ,",
],
# side group top edge
's1':[
", o . . . . x . o ,",
", O x . x . X X O ,",
", O X X X o X O O ,",
", O O O O O O , , ,",
", , , , , , , , , ,",
],
's2':[
", O . . . . . . O ,",
", O x X x . x X O ,",
", O X X o X X O , ,",
", , O O O O O O , ,",
", , , , , , , , , ,",
],
'c3':[
". . . o . X O ,",
". x . . X X O ,",
". . X . O O , ,",
"o X X O , , , ,",
". X O O , , , ,",
". X O , , , , ,",
"x O , , , , , ,",
", , , , , , , ,",
],
}
name=sys.argv[1];tm=int(sys.argv[2]);mind=int(sys.argv[3])
keys={'c1':['cd'] if False else ['dc'],'c2':['dc'],'s1':['db'],'s2':['db'],'c3':['cd']}[name]
box=(0,0,len(FR[name][0].split())-1,len(FR[name])-1)
run(FR[name],tm,2,keys,box,mind=mind,maxwin=2,show_n=25)
