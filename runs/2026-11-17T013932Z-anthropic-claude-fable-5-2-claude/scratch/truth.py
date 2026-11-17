import sys, os, time; sys.path.insert(0,'scratch')
from tsu import *
from cands import C
name=sys.argv[1]; moves=sys.argv[2].split(',') if len(sys.argv)>2 and sys.argv[2]!='-' else []
s=C[name]; diag=s['diag'].replace('/','\n')
for label,env in (('default',{}),('seed7',{'TSEED':'7'}),('NOTT',{'NOTT':'1'}),('NOTT+seed7',{'NOTT':'1','TSEED':'7'})):
    for k in ('TSEED','NOTT','ROBUST'): os.environ.pop(k,None)
    os.environ.update(env)
    p=Problem(diag, defender='W', first=s['first'], maxnodes=int(sys.argv[3]) if len(sys.argv)>3 else 300000000)
    t=time.time(); st,v=p.query(moves); p.close()
    print(label.ljust(12), st or sorted(v.items()), '%.1fs'%(time.time()-t))
