from tl import *
D = """
X X X X X X , ,
O O O O O X X ,
. . x . O O X ,
. . . O . O X ,
"""
sp = dspec(D, 'ap', 'W', 'live', 'eq')
explore(sp)
sp2 = dspec(D, 'ap', 'B', 'kill', 'eq')
explore(sp2)
