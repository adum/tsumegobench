import sys
from design import load
import etree
d, prob = load(sys.argv[1])
for s in sys.argv[2:]:
    seq = [m for m in s.split(',') if m]
    print('==', s)
    etree.wrong_report(prob, prob.board, d['first'], seq, d['solver'], d['objective'])
