import sys, glob
from gotools import *
import minedload, etree, gentree
from rever import fix_target
from mine5 import tree_stats, branch_count

out = open(sys.argv[1], 'w')
files = sys.argv[2:]
for fn in files:
    try:
        cs = minedload.parse_file(fn)
    except Exception as e:
        continue
    for c in cs:
        try:
            c = fix_target(c)
            if len(c['target']) < 3:
                continue
            prob = minedload.to_problem(c)
            b = prob.board
            etree._cache.clear(); etree._scache.clear()
            etree.MAXNODES = 1_500_000
            res, overall, stats = classify(prob, b, c['solver'], c['solver'], c['objective'], maxnodes=1_500_000)
            if any(v == -2 for v in overall.values()):
                continue
            wins = [m for m, v in res.items() if v == 'win']
            if len(wins) != 1 or wins[0] == 'pass':
                continue
            st = status(prob, b, opp(c['solver']), c['solver'], c['objective'])
            if st != 'lose':
                continue
            frags = gentree.gen(prob, b, c['solver'], c['objective'], maxans=2)
            d, n, s = tree_stats(frags)
            bc = branch_count(prob, b, c['solver'], c['objective'])
            kos = sum(1 for v in res.values() if v in ('ko', 'seki'))
            out.write('%s | %s | key=%s depth=%d nodes=%d branch=%d kos=%d | %s\n' % (fn, c['hdr'][:40], wins[0], d, n, bc, kos, s[:200]))
            out.flush()
        except Exception as e:
            continue
out.write('done\n')
out.close()
