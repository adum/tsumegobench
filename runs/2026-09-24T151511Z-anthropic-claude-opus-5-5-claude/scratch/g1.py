from rnd import *
FR={
'G1':([
"? ? ? ? . X O ,",
"? ? ? ? X X O ,",
"? ? ? X O O , ,",
"? ? X X O , , ,",
". X X O , , , ,",
"X O O , , , , ,",
"O O , , , , , ,",
],['dc'],2),
'G2':([
"? ? ? ? ? . O ,",
"? ? ? ? ? O X ,",
"? ? ? ? O X X ,",
"O O O O X X , ,",
"X X X X , , , ,",
],['ed'],1),
'G3':([
", X . ? ? ? ? . X ,",
", X O ? ? ? ? O X ,",
", X O O O O O O X ,",
", , X X X X X X , ,",
],['cb'],1),
'G4':([
", O . ? ? ? ? . O ,",
", O X ? ? ? ? X O ,",
", O X X X X X X O ,",
", , O O O O O O , ,",
],['cb'],2),
}
name=sys.argv[1];tm=int(sys.argv[2]);seed=int(sys.argv[3])
fr,keys,att=FR[name]
box=(0,0,len(fr[0].split())-1,len(fr)-1)
rrun(fr,tm,att,keys,box,n=4000,seed=seed,mind=int(sys.argv[4]))
