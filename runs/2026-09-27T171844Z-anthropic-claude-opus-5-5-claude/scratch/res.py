import json
import sys
import os

for rid in sys.argv[1:]:
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'originality', 'results', rid + '.json')
    if not os.path.exists(fn):
        print(rid, 'NOT READY')
        continue
    d = json.load(open(fn))
    gp = d.get('goProblems') or {}
    loc = d.get('local') or {}
    print(rid, d['status'], 'remaining=%s' % d['queriesRemaining'], 'sha=%s' % (d['candidateSha256'] or '')[:12])
    print('  local closest:', loc.get('closestReferenceMatch'), 'builtin:', loc.get('builtInSetupMatch'),
          'peers:', loc.get('peerExactMatches'), loc.get('peerShapeMatches'))
    print('  signature matches:', gp.get('signatureMatches'), 'top%:', gp.get('topPercentage'))
    for m in (gp.get('percentageMatches') or [])[:5]:
        print('   ', m.get('id'), m.get('percentage'), m.get('difficulty'))
    if d.get('errors'):
        print('  errors:', d['errors'])
