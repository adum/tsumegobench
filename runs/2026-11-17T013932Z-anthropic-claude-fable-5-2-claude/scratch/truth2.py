import sys, os, time; sys.path.insert(0,'scratch')
from tsu import *
from cands import C, FINAL
names=sys.argv[1].split(',')
cap=int(sys.argv[2])
for name in names:
    s=C[name]; diag=s['diag'].replace('/','\n')
    res={}
    for label,env in (('seed0',{'TSEED':'0'}),('NOTT',{'NOTT':'1'})):
        for k in ('TSEED','NOTT','ROBUST'): os.environ.pop(k,None)
        os.environ.update(env)
        p=Problem(diag, defender='W', first=s['first'], maxnodes=cap)
        t=time.time(); st,v=p.query([]); p.close()
        res[label]=(sorted(v.items()), time.time()-t)
    same = res['seed0'][0]==res['NOTT'][0]
    print(name, 'SAME' if same else 'DIFF', 'tt %.1fs nott %.1fs'%(res['seed0'][1],res['NOTT'][1]))
    if not same:
        print('   tt  ', res['seed0'][0]); print('   nott', res['NOTT'][0])
