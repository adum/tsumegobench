import sys, json, time, os
n=int(sys.argv[1]); tag=sys.argv[2]
rid='problem-%02d-%s'%(n,tag)
req='originality/requests/%s.json'%rid
assert not os.path.exists(req), 'request id reused'
json.dump({'requestId':rid,'path':'outputs/problem-%02d.sgf'%n}, open(req,'w'))
res='originality/results/%s.json'%rid
for i in range(150):
    if os.path.exists(res):
        time.sleep(0.5)
        d=json.load(open(res))
        print(rid, 'STATUS', d['status'], 'remaining', d['queriesRemaining'], 'sha', d['candidateSha256'][:12])
        print(' local', json.dumps(d.get('local')))
        g=d.get('goProblems') or {}
        print(' sig', [(m['id'],m['difficulty']) for m in g.get('signatureMatches',[])])
        print(' top', g.get('topPercentage'), [(m['id'],m['percentage'],m['difficulty']) for m in g.get('percentageMatches',[])[:8]])
        print(' errors', d.get('errors'))
        break
    time.sleep(1)
else:
    print('no result yet for', rid)
