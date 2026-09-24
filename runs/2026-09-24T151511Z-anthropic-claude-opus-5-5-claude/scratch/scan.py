import sys,glob
items=[]
for fn in sys.argv[1:]:
    L=open(fn).read().split('\n')
    for i,l in enumerate(L):
        if l.startswith('FOUND'):
            parts=l.split()
            try:
                ni=parts.index('nodes');nn=int(parts[ni+1]);ml=int(parts[ni+2])
            except: continue
            bd=[];j=i+1
            while j<len(L) and not L[j].startswith(('TREE','FOUND')):bd.append(L[j]);j+=1
            tr=L[j] if j<len(L) else ''
            items.append((ml,nn,fn,l,bd,tr))
items.sort(key=lambda x:(-x[0],x[1]))
for ml,nn,fn,l,bd,tr in items[:int(__import__('os').environ.get('TOP','12'))]:
    print(fn,l);print('\n'.join(bd));print(tr[:400]);print()
