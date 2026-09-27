"""Load mined candidates from miner output files into Problem objects."""
import re
from gotools import *


def parse_file(fn):
    out = []
    lines = open(fn).read().split('\n')
    i = 0
    while i < len(lines):
        L = lines[i]
        if L.startswith('#'):
            hdr = L
            m = re.search(r'solver=(\w) obj=(\w+) key=(\w+)', L)
            solver = BLACK if m.group(1) == 'B' else WHITE
            obj = m.group(2)
            key = m.group(3)
            b = Board()
            j = i + 2
            while j < len(lines) and re.match(r'^[a-s][0-9 ][0-9] ', lines[j]):
                row = lines[j]
                y = ord(row[0]) - 97
                cells = row[4:].split(' ')
                for x, ch in enumerate(cells):
                    if ch == 'X':
                        b.b[xy2i(x, y)] = BLACK
                    elif ch == 'O':
                        b.b[xy2i(x, y)] = WHITE
                j += 1
            region = set(sgf2i(s) for s in lines[j].split(' ')[1].split(','))
            safe = set(sgf2i(s) for s in lines[j + 1].split(' ')[1].split(',') if s)
            target = set(sgf2i(s) for s in lines[j + 2].split(' ')[1].split(',') if s)
            att = solver if obj == 'kill' else opp(solver)
            out.append(dict(hdr=hdr, board=b, region=region, safe=safe, target=target, att=att,
                            solver=solver, objective=obj, key=key))
            i = j + 3
        else:
            i += 1
    return out


def to_problem(c):
    return Problem(c['board'], c['region'], c['safe'], c['target'], c['att'])
