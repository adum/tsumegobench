from build import *
import cl
def ko_in_tree(ctx,ch):
    hits=[]
    for p in paths(ch):
        b=ctx.b;ko=None;tm=ctx.tomove
        for c,m,cm in p:
            r=play(b,P(m),tm,ko);b,ko=r;tm=3-tm
            if ko is not None:hits.append([x[1] for x in p]);break
    return hits
def depth_consistency(ctx,moves=()):
    b,ko,tm=ctx.seq(list(moves))
    out=[]
    for d in (30,45,60):
        cl.lib.ld_init  # noop
        res=[]
        for p,nb_,nk in ctx.cs.moves(b,tm,ko):
            res.append((S(p),ctx.cs.win(nb_,3-tm,nk,depth=d)))
        out.append(res)
    return out
