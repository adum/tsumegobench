import sys; sys.path.insert(0,'scratch')
from tsu import *
p = Problem("""
X@+++@X..
X@@@@@X..
XXXXXXX..
""", defender='W', first='B')
print(p.show())
print(p.report())
p2 = Problem("""
X@+++@X..
X@@@@@X..
XXXXXXX..
""", defender='W', first='W')
print(p2.report())
# bulky five / L-group style corner test: classic "L group" is dead
p3 = Problem("""
+++@X..
+++@X..
@@@@X..
XXXXX..
""", defender='W', first='W')
print(p3.report())
p4 = Problem("""
+++@X..
+++@X..
@@@@X..
XXXXX..
""", defender='W', first='B')
print(p4.report())
b = Builder(p4); r = b.build(); print('\n'.join(dump(p4,r))); print(to_sgf(p4,r))
