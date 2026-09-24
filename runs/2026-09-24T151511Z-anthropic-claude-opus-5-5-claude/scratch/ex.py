from tool import *
import sys
def explore(d,tomove,attacker,keys,box,maxd=20):
    s,b=analyze(d,tomove,attacker,keys,box,maxd)
    # for each first move, show opponent best reply
    for p,nb_,nk in s.moves(b,tomove,None):
        rep=[]
        for q,nb2,nk2 in s.moves(nb_,3-tomove,nk):
            dd=s.dist(nb2,tomove,nk2,maxd)
            rep.append((S(q),dd))
        print(S(p),'->',rep)
