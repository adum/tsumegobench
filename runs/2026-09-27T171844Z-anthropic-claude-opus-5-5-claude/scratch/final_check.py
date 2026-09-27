import sys
from final import P, make
from validate import check
for n in [int(x) for x in sys.argv[1:]]:
    sgf, spec = make(n)
    print('==== problem %02d' % n, flush=True)
    errs = check(sgf, spec, verbose=True)
    print('RESULT', n, 'ERRORS' if errs else 'OK', flush=True)
