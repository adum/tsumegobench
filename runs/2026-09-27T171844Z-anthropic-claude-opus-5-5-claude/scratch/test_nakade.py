from gotools import *
from explore import explore
import time
# bulky five in top-left: eye aa ba ca ab bb, white wall around, black safe outside
rows = [
 "...OB-",
 "..OOB-",
 "OOOBB-",
 "BBBB--",
]
b, region, safe, target = diagram(rows)
target = {i for i in range(361) if b.b[i] == WHITE}
prob = Problem(b, region, safe, target, BLACK)
t = time.time()
explore(prob, [], BLACK, 'kill', BLACK, (0,0,6,4))
print(time.time()-t)
# bigger: rabbity six / 7-space
rows = [
 "....OB-",
 "...OOB-",
 "OOOO.OB",
 "BBBBOOB",
 "----BB-",
]
b, region, safe, target = diagram(rows)
target = {i for i in range(361) if b.b[i] == WHITE}
prob = Problem(b, region, safe, target, BLACK)
t = time.time()
explore(prob, [], BLACK, 'kill', BLACK, (0,0,7,5))
print(time.time()-t)
