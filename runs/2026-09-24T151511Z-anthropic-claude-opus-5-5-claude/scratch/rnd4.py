from rnd2 import *
import cl
FR4={
'S1':([   # black side group top edge, white outside
", O ? ? ? ? ? ? O ,",
", O ? ? ? ? ? ? O ,",
", O X X X X X X O ,",
", , O O O O O O , ,",
],['cc'],2),
'S2':([   # white side group
", X ? ? ? ? ? ? X ,",
", X ? ? ? ? ? ? X ,",
", X O O O O O O X ,",
", , X X X X X X , ,",
],['cc'],1),
'K5':([   # black corner group 5x4 interior
"? ? ? ? ? X O ,",
"? ? ? ? ? X O ,",
"? ? ? ? ? X O ,",
"? ? ? ? X X O ,",
"X X X X X O , ,",
"O O O O O , , ,",
],['fd'],2),
'K6':([
"? ? ? ? ? O X ,",
"? ? ? ? ? O X ,",
"? ? ? ? ? O X ,",
"? ? ? ? O O X ,",
"O O O O O X , ,",
"X X X X X , , ,",
],['fd'],1),
}
FR4.update({
'K7':([   # black corner group 3 tall 6 wide
"? ? ? ? ? ? X O ,",
"? ? ? ? ? ? X O ,",
"? ? ? ? ? X X O ,",
"X X X X X X O , ,",
"O O O O O O , , ,",
],['fd'],2),
'K8':([   # white corner group 3 tall 6 wide
"? ? ? ? ? ? O X ,",
"? ? ? ? ? ? O X ,",
"? ? ? ? ? O O X ,",
"O O O O O O X , ,",
"X X X X X X , , ,",
],['fd'],1),
})
from rnd3 import FR3
FR4.update(FR3)

if __name__=='__main__':
    import rnd2;rnd2.LIMIT[0]=int(sys.argv[6]) if len(sys.argv)>6 else 30000
    cl.set_limit(rnd2.LIMIT[0])
    name=sys.argv[1];tm=int(sys.argv[2]);seed=int(sys.argv[3])
    fr,keys,att=FR4[name]
    box=(0,0,len(fr[0].split())-1,len(fr)-1)
    rrun2(fr,tm,att,keys,box,n=int(sys.argv[5]),seed=seed,mind=int(sys.argv[4]),w={'.':0.5,'X':0.25,'O':0.25},minbusy=6,maxnodes=90,minml=int(sys.argv[7]) if len(sys.argv)>7 else 0)
