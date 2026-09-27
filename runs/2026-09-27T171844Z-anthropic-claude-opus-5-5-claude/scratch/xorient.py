import sys
from build import build
from validate import check
import final
n = int(sys.argv[1]); t = int(sys.argv[2])
p = final.P[n]
sgf, spec = build(p['design'], p['tree'], t, shift=(0, 0), swap=p.get('swap', False))
errs = check(sgf, spec, verbose=False)
print('XORIENT', n, 't=%d' % t, 'ERRORS' if errs else 'OK', flush=True)
