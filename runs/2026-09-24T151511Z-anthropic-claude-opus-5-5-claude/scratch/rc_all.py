from refchk import *
import sys
P01=([". . O . . X O ,","O . . O . X O ,","X X . X X X O ,","X X X X X O , ,","O O O O O , , ,"],1,2,['ed'],(0,0,7,4),"(bb R)(aa bb)(ba bb)(cb bb)(cc bb)(da bb)(eb bb)")
P02=([", X . O O X X O X ,",", X . . O . . O X ,",", X O O O O O O X ,",", , X X X X X X , ,"],2,1,['cc'],(0,0,9,3),"(cb (fb gb R)(gb fb R))(ca cb)(db ca)(fb cb)(gb cb)")
P03=([". O . X X O ,","O . O . X O ,","X . . . X O ,","X X . X X O ,","X X X X O , ,","O O O O , , ,"],2,2,['ed'],(0,0,6,5),"(cc (bb bc R)(bc bb R))(aa ca)(ca bb)(bb cc)(db bb)(bc cc)(dc bc)(cd bb)")
P04=([", O . X . X . . O ,",", O X . . . . . O ,",", O X X X X X X O ,",", , O O O O O O , ,"],2,2,['cc'],(0,0,9,3),"(eb (hb ha R)(fb hb R)(db ha R))(ca ha)(ea eb)(ga ha)(ha eb)(db ha)(fb eb)(gb eb)(hb eb)")
for name in sys.argv[1:]:
    t=time.time();print(name);ref_check(*globals()[name]);print(time.time()-t)
