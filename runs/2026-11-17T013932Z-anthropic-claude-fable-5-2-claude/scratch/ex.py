import sys; sys.path.insert(0,'scratch')
from d import *
p=get(sys.argv[1])
for a in sys.argv[2:]:
    s=tuple(a.split(',')) if a!='-' else ()
    print('--- after', ' '.join(s)); explore(p, s)
