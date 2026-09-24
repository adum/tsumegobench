import sys,re
for fn in sys.argv[1:]:
    L=open(fn).read().split('\n')
    items=[]
    i=0
    while i<len(L):
        if L[i].startswith('TREE'):
            t=L[i];f=L[i+1];j=i+2;bd=[]
            while j<len(L) and not L[j].startswith(('TREE','FOUND','auto')) and L[j].strip():bd.append(L[j]);j+=1
            nn=int(t.split()[1]);d=int(f.split()[2])
            items.append((d,nn,f,t,bd));i=j
        else:i+=1
    items.sort(key=lambda x:(-x[0],x[1]))
    print('=====',fn)
    for d,nn,f,t,bd in items[:int(sys.argv[0] and 6)]:
        print(f,'nodes',nn);print('\n'.join(bd[1:]));print(t[:300])
