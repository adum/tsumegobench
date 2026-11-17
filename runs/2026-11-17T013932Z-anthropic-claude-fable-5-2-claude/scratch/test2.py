import sys, time; sys.path.insert(0,'scratch')
from tsu import *
tests = {
 'side7x2': """
X+++++++X
X@+++++@X
XX@@@@@XX
..XXXXX..
""",
 'corner12': """
+++++@X
++++@@X
+++@XXX
@@@@X..
XXXXX..
""",
 'side14': """
.a+++++++a.
.X@+++++@X.
.X@@+++@@X.
.XXX@@@XXX.
...XXXXX...
""",
}
for name, d in tests.items():
    for first in 'BW':
        p = Problem(d, defender='W', first=first, maxnodes=20000000)
        t = time.time()
        print(name, first, p.report(), '%.2fs' % (time.time()-t))
        p.close()
