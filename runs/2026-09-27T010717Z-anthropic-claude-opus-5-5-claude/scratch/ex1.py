from tl import *
import json,glob
recs=[json.loads(l) for f in glob.glob('cands_side_*.jsonl') for l in open(f)]
r=[r for r in recs if r['goal']=='kill' and r['move']=='hb' and r['depth']==14 and len(r['AB'])+len(r['AW'])==28][0]
print(r)
sp=Spec(r['AB'],r['AW'],r['region'],'B','kill',r['key'])
explore(sp)
explore(sp, ['hb'], False)
