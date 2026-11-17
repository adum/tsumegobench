import sys, json, glob; sys.path.insert(0,'scratch')
from build import *
from multiprocessing import Pool

def work(d):
    p=Problem(d['diag'], defender='W', first=d['first'], maxnodes=1500000)
    try:
        b=B2(p, wrong_root=[], inner={}, inner_wrong=0, max_right_len=11)
        root=b.build()
        d['rnodes']=count_nodes(root); d['rdepth']=max_depth(root)
        # min depth of right leaves along principal (max over replies, min over wins)
        def D(n, solver):
            if not n.children: return 0
            if solver: return 1+min(D(c, False) for c in n.children)
            return 1+max(D(c, True) for c in n.children) if n.children else 0
        d['pdepth']=D(root, True)
        st,v=p.query([])
        d['nmoves']=len(v)-1
    except Exception as e:
        d['err']=str(e)[:100]
    finally:
        p.close()
    return d

if __name__=='__main__':
    rows=[]; seen=set()
    for fn in sorted(glob.glob('scratch/out/*.jsonl')):
        if 'pool' in fn: continue
        for i,l in enumerate(open(fn)):
            if l.startswith('#') or not l.strip(): continue
            d=json.loads(l); k=(d['diag'],d['first'])
            if k in seen: continue
            seen.add(k); d['src']='%s:%d'%(fn.split('/')[-1].replace('.jsonl',''),i); rows.append(d)
    print(len(rows),'unique')
    with Pool(7) as pool:
        out=pool.map(work, rows, chunksize=4)
    with open('scratch/out/pool.json','w') as f:
        json.dump(out,f)
    import collections
    c=collections.Counter((d['first'],d.get('pdepth')) for d in out)
    print(sorted(c.items(), key=str))
