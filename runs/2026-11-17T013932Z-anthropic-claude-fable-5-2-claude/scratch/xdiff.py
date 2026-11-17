import sys, os; sys.path.insert(0,'scratch')
from build import *
from dr import tdump
from cands import C
name=sys.argv[1]
s=C[name]; diag=s['diag'].replace('/','\n')
p=Problem(diag, defender='W', first=s['first'], maxnodes=20000000)
root=B2(p, **s.get('kw',{})).build()
open('scratch/out/xd_%s_%s.txt'%(name, os.environ.get('TSEED','0')),'w').write('\n'.join(tdump(root))+'\n')
p.close()
