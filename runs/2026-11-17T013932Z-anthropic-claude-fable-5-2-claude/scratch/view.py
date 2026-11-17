import sys, json, glob
pat = sys.argv[1]; first = sys.argv[2] if len(sys.argv)>2 else None
mind = int(sys.argv[3]) if len(sys.argv)>3 else 3
maxd = int(sys.argv[4]) if len(sys.argv)>4 else 99
limit = int(sys.argv[5]) if len(sys.argv)>5 else 30
skip = int(sys.argv[6]) if len(sys.argv)>6 else 0
rows=[]
for fn in sorted(glob.glob(pat)):
    for i,line in enumerate(open(fn)):
        if line.startswith('#'): continue
        d=json.loads(line); d['src']='%s:%d'%(fn.split('/')[-1],i); rows.append(d)
rows=[d for d in rows if (not first or d['first']==first) and mind<=d['depth']<=maxd]
rows.sort(key=lambda d:(-d['traps'],-len(d['kos']),-d['depth']))
print(len(rows),'rows')
sel=rows[skip:skip+limit]
# print 4 per row
for i in range(0,len(sel),4):
    chunk=sel[i:i+4]
    hdr=[('%s %s k=%s d%d t%d ko%d'%(d['src'].replace('.jsonl',''),d['first'],d['key'],d['depth'],d['traps'],len(d['kos']))) for d in chunk]
    print('   '.join(h.ljust(34) for h in hdr))
    grids=[d['diag'].split('\n') for d in chunk]
    for r in range(max(len(g) for g in grids)):
        print('   '.join((' '.join(g[r]) if r<len(g) else '').ljust(34) for g in grids))
    print()
