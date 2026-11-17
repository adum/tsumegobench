import sys; sys.path.insert(0,'scratch')
from dr import *
from specs import SPECS
for n in [int(a) for a in sys.argv[1].split(',')]:
    s=SPECS[n]; print('=====', n)
    kw=eval('dict(%s)'%sys.argv[2]) if len(sys.argv)>2 else dict(K=1)
    dr(s['diag'], s['first'], **kw)
