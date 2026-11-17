import sys; sys.path.insert(0,'scratch')
from tsu import *
tests = {
 'rect6 0 libs (dead)': "+++@X.\n+++@X.\n@@@@X.\nXXXXX.",
 'rect6 1 lib (ko)': "+++@XX\n+++@aX\n@@@@XX\nXXXXX.",
 'rect6 2 libs (alive)': "+++@XX.\n+++@aX.\n@@@@XX.\nXaXXX..\nXXX....",
 'L+1 group? (straight 2x4 corner 8: alive)': "++++@X\n++++@X\n@@@@@X\nXXXXXX",
 'bulky five side': "X@@@@X\nX@++@X\nX@+++X\nXXXXXX",
}
for name, d in tests.items():
    p = Problem(d, defender='W', first='B', maxnodes=20000000)
    print(name, '| B first:', p.report()); p.close()
