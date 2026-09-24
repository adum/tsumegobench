from find2 import *
def ex(d,tomove,attacker,keys,box,replies=True):
    b=parse([r.replace(' ','') for r in d])
    outs=[y*N+x for y,r in enumerate(d) for x,ch in enumerate(r.replace(' ','')) if ch==',']
    if not legal(b):print('WARNING: some group has <2 liberties')
    show(b,(box[0],box[1],box[2]+1,box[3]+1))
    r=evalpos(b,tomove,attacker,keys,box,outs)
    if not r:
        s=CS(b,box,attacker,keys,outs);print('bad: status',s.status(b),'pass-> att wins',s.win(b,3-tomove));return
    s,wins,res=r
    print('WINS',wins)
    if not replies:return s,b
    for p,nb_,nk in s.moves(b,tomove):
        line=[]
        for q,nb2,nk2 in s.moves(nb_,3-tomove,nk):
            w=s.win(nb2,tomove,nk2)
            good_for_mover2 = (w==(3-tomove==attacker))
            if good_for_mover2:
                line.append(S(q))
        print(S(p),'W' if S(p) in wins else '-', 'opp good replies:',line)
    return s,b
