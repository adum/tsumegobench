#!/bin/bash
# usage: q.sh reqid problemnum
cd ..
echo "{\"requestId\":\"$1\",\"path\":\"outputs/problem-$2.sgf\"}" > originality/requests/$1.json
for i in $(seq 1 60); do [ -f originality/results/$1.json ] && break; sleep 2; done
python3 -c "
import json;r=json.load(open('originality/results/$1.json'))
print(r['status'],r['queriesRemaining'],r.get('errors'))
l=r.get('local',{});print('local',l.get('builtInSetupMatch'),l.get('exactReferenceMatch'),l.get('peerExactMatches'),l.get('peerShapeMatches'))
g=r.get('goProblems') or {}
print('sig',[m['id'] for m in g.get('signatureMatches',[])],'top%',g.get('topPercentage'))
"
