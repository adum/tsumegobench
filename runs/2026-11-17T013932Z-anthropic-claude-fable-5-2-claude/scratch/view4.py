import sys, json, glob
first=sys.argv[1]; lo=int(sys.argv[2]); hi=int(sys.argv[3]); rmax=int(sys.argv[4]); limit=int(sys.argv[5]); skip=int(sys.argv[6]) if len(sys.argv)>6 else 0
rows=[]; seen=set()
for fn in sorted(glob.glob('scratch/out/'+__import__('os').environ.get('PAT','g3*')+'.jsonl')):
    for i,l in enumerate(open(fn)):
        if l.startswith('#') or not l.strip(): continue
        try: d=json.loads(l)
        except Exception: continue
        if (d['diag'],d['first']) in seen: continue
        seen.add((d['diag'],d['first']))
        d['src']='%s:%d'%(fn.split('/')[-1].replace('.jsonl',''),i); rows.append(d)
print(len(rows),'total')
rows=[d for d in rows if ('EDGE' in __import__('os').environ or (d['key'][1]!='a' and d['key'][0]!='a')) and (first=='*' or d['first']==first) and lo<=len(d['pv'])<=hi and d['rnodes']<=rmax]
rows.sort(key=lambda d:(-len(d['pv']), -(d['traps']+len(d['kos'])), d['src']))
print(len(rows),'rows')
sel=rows[skip:skip+limit]
N=5
for i in range(0,len(sel),N):
    chunk=sel[i:i+N]
    hdr=[('%s %s%s pv%d r%d t%d k%d m%d'%(d['src'],d['first'],d['key'],len(d['pv']),d['rnodes'],d['traps'],len(d['kos']),d['nmoves'])) for d in chunk]
    print('  '.join(h.ljust(29) for h in hdr))
    grids=[d['diag'].split('\n') for d in chunk]
    for r in range(max(len(g) for g in grids)):
        line='  '.join((' '.join(g[r]) if r<len(g) else '').ljust(29) for g in grids)
        if line.strip('. '): print(line)
    print()
