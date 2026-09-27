"""Export a mined candidate to designs.py-style rows (top-left orientation)."""
import sys
from gotools import *
import minedload
from rever import fix_target

fn, idx, name = sys.argv[1], sys.argv[2], sys.argv[3]
cs = minedload.parse_file(fn)
c = [c for c in cs if c['hdr'].startswith('#%s ' % idx)][0]
c = fix_target(c)
b = c['board']
xs = [i % N for i in range(361) if b.b[i] or i in c['region']]
ys = [i // N for i in range(361) if b.b[i] or i in c['region']]
rows = []
for y in range(0, max(ys) + 1):
    row = ''
    for x in range(0, max(xs) + 1):
        i = xy2i(x, y)
        v = b.b[i]
        if v == EMPTY:
            row += '.' if i in c['region'] else '-'
        elif i in c['safe']:
            row += 'B' if v == BLACK else 'W'
        else:
            if i in c['target']:
                row += 'x' if v == BLACK else 'o'
            else:
                row += 'X' if v == BLACK else 'O'
    rows.append(row)
att = 'BLACK' if c['att'] == BLACK else 'WHITE'
first = 'BLACK' if c['solver'] == BLACK else 'WHITE'
print("D['%s'] = dict(" % name)
print("    rows=[")
for r in rows:
    print('        "%s",' % r)
print("    ],")
print("    att=%s, first=%s, solver=%s, objective='%s'," % (att, first, first, c['objective']))
print(")")
