import sys, os, hashlib; sys.path.insert(0,'scratch')
from mk import *
from cands import FINAL
for slot,name in sorted(FINAL.items()):
    if len(sys.argv)>1 and str(slot) not in sys.argv[1].split(','): continue
    sgf=mk(name, slot, verbose=False, board='-b' in sys.argv)
    print('   sha', hashlib.sha256(open('outputs/problem-%02d.sgf'%slot,'rb').read()).hexdigest()[:12])
