from rnd2 import *
import cl
FR3={
'K1':([   # black corner group, white outside: interior 4x4 random
"? ? ? ? X O ,",
"? ? ? ? X O ,",
"? ? ? ? X O ,",
"? ? ? ? X O ,",
"X X X X O , ,",
"O O O O , , ,",
],['ed'],2),
'K2':([   # white corner group
"? ? ? ? O X ,",
"? ? ? ? O X ,",
"? ? ? ? O X ,",
"? ? ? O O X ,",
"O O O O X , ,",
"X X X X , , ,",
],['ed'],1),
'K3':([   # black corner group, 5 wide, 3 tall
"? ? ? ? ? X O ,",
"? ? ? ? ? X O ,",
"? ? ? ? X X O ,",
"X X X X X O , ,",
"O O O O O , , ,",
],['ed'],2),
'K4':([   # white corner group, 5 wide, 3 tall
"? ? ? ? ? O X ,",
"? ? ? ? ? O X ,",
"? ? ? ? O O X ,",
"O O O O O X , ,",
"X X X X X , , ,",
],['ed'],1),
}
if __name__=='__main__':
    cl.set_limit(int(sys.argv[6]) if len(sys.argv)>6 else 30000)
    name=sys.argv[1];tm=int(sys.argv[2]);seed=int(sys.argv[3])
    fr,keys,att=FR3[name]
    box=(0,0,len(fr[0].split())-1,len(fr)-1)
    rrun2(fr,tm,att,keys,box,n=int(sys.argv[5]),seed=seed,mind=int(sys.argv[4]),w={'.':0.5,'X':0.25,'O':0.25},minbusy=6)
