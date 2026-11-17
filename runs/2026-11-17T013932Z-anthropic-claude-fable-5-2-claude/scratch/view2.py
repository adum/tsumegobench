import sys, json
first=sys.argv[1]; lo=int(sys.argv[2]); hi=int(sys.argv[3]); limit=int(sys.argv[4]); skip=int(sys.argv[5]) if len(sys.argv)>5 else 0
maxinner=int(sys.argv[6]) if len(sys.argv)>6 else 9
rows=json.load(open('scratch/out/pool.json'))
rows=[d for d in rows if 'err' not in d and d['first']==first and lo<=d['pdepth']<=hi]
for d in rows:
    d['inner']=d['diag'].count('x')+d['diag'].count('o')
rows=[d for d in rows if d['inner']<=maxinner]
rows.sort(key=lambda d:(-(d['traps']+len(d['kos'])), d['inner'], d['src']))
print(len(rows),'rows')
sel=rows[skip:skip+limit]
N=5
for i in range(0,len(sel),N):
    chunk=sel[i:i+N]
    hdr=[('%s %s p%d r%d t%d k%d m%d'%(d['src'],d['key'],d['pdepth'],d['rnodes'],d['traps'],len(d['kos']),d['nmoves'])) for d in chunk]
    print('  '.join(h.ljust(27) for h in hdr))
    grids=[d['diag'].split('\n') for d in chunk]
    for r in range(max(len(g) for g in grids)):
        line='  '.join((' '.join(g[r]) if r<len(g) else '').ljust(27) for g in grids)
        if line.strip('. '): print(line)
    print()
