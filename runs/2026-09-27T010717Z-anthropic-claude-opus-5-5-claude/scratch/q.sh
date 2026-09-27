#!/bin/zsh
# usage: q.sh requestId problemNN
cd /Users/adammiller/code/tsumegobench/runs/2026-09-27T010717Z-anthropic-claude-opus-5-5-claude
echo "{\"requestId\": \"$1\", \"path\": \"outputs/problem-$2.sgf\"}" > originality/requests/$1.json
until [ -f originality/results/$1.json ]; do sleep 2; done
python3 -c "
import json; r=json.load(open('originality/results/$1.json')); print(r['status'], 'remaining', r['queriesRemaining'], 'sha', r['candidateSha256'][:12]); print('local', r['local']['closestReferenceMatch'], r['local'].get('peerShapeMatches'), r['local'].get('peerExactMatches')); g=r.get('goProblems') or {}; print('sig', g.get('signatureMatches'), 'top', g.get('topPercentage')); print((g.get('percentageMatches') or [])[:3]); print(r.get('errors'))"
