from find2 import *
import sys
fr=[
". . ? . O , ,",
". ? . X O , ,",
"? . X X O , ,",
"? X ? O O , ,",
". X O , , , ,",
"? O , , , , ,",
", , , , , , ,",
]
tm=int(sys.argv[1])
run(fr,tm,2,['dc'],(0,0,6,6),mind=int(sys.argv[2]),maxwin=1,show_n=40)
