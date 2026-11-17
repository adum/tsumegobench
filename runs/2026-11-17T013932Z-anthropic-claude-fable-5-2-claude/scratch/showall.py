import sys, re; sys.path.insert(0,'scratch')
from tsu import pt
def board(sgf):
    ab=re.search(r'AB((?:\[\w\w\])+)',sgf).group(1); aw=re.search(r'AW((?:\[\w\w\])+)',sgf).group(1)
    g={}
    for p in re.findall(r'\[(\w\w)\]',ab): g[p]='X'
    for p in re.findall(r'\[(\w\w)\]',aw): g[p]='O'
    xs=[ord(p[0])-97 for p in g]; ys=[ord(p[1])-97 for p in g]
    x0,x1=max(0,min(xs)-1),min(18,max(xs)+1); y0,y1=max(0,min(ys)-1),min(18,max(ys)+1)
    out=['    '+' '.join(chr(97+x) for x in range(x0,x1+1))]
    for y in range(y0,y1+1):
        out.append('  %s '%chr(97+y)+' '.join(g.get(pt(x,y),'.') for x in range(x0,x1+1)))
    return '\n'.join(out)
for n in range(1,11):
    s=open('outputs/problem-%02d.sgf'%n).read()
    first=re.search(r';([BW])\[',s).group(1)
    print('problem %02d  first=%s  len=%d'%(n,first,len(s)))
    print(board(s)); print()
