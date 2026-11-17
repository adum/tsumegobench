"""Enumerate '?' variants of a frame; report variants with a unique winning first move.
usage: python3 scratch/enum.py framefile [opts=+xo] [maxnodes]
Frame file: frames separated by lines starting with '#name'.
Attacker is always Black (X/x), defender White (O/o/@) in the authoring frame.
"""
import sys, itertools, time
sys.path.insert(0, 'scratch')
from tsu import *


class _Budget(Exception):
    pass


def depth_metric(p, best=2, cap=9, budget=250):
    cnt = [0]

    def q(moves):
        key = tuple(moves)
        if key not in p.cache:
            cnt[0] += 1
            if cnt[0] > budget:
                raise _Budget()
        return p.query(list(moves))

    def D(moves, d):
        if d >= cap:
            return 0
        st, v = q(moves)
        if st:
            return 0
        wins = [m for m, x in v.items() if x >= best and m != 'pass']
        if not wins:
            return 99
        return min(1 + E(moves + (m,), d + 1) for m in wins)

    def E(moves, d):
        if d >= cap:
            return 0
        st, v = q(moves)
        if st:
            return 0
        worst = 0
        for r in v:
            if r == 'pass':
                continue
            st2, v2 = q(moves + (r,))
            if st2:
                continue
            if v2.get('pass', 0) >= best:
                continue
            worst = max(worst, 1 + D(moves + (r,), d + 1))
        return worst

    try:
        return D((), 0)
    except _Budget:
        return cap


def variants(frame, opts):
    rows = frame.strip('\n').split('\n')
    qs = [(y, x) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch == '?']
    for combo in itertools.product(opts, repeat=len(qs)):
        g = [list(r) for r in rows]
        for (y, x), ch in zip(qs, combo):
            g[y][x] = ch
        yield ''.join(combo), '\n'.join(''.join(r) for r in g)


def analyse(diag, maxnodes=2000000, want_depth=True):
    out = []
    for first in 'BW':
        p = Problem(diag, defender='W', first=first, maxnodes=maxnodes)
        try:
            st, v = p.query([])
            if st or any(x < 0 for x in v.values()):
                continue
            wins = [m for m, x in v.items() if x == 2 and m != 'pass']
            kos = [m for m, x in v.items() if x == 1 and m != 'pass']
            if v.get('pass', 0) == 2:
                continue
            if len(wins) != 1:
                continue
            # the opponent moving first must change the outcome fully or to ko -- record pass value
            dm = depth_metric(p) if want_depth else -1
            out.append((first, wins[0], kos, v.get('pass'), dm, len(v) - 1))
        finally:
            p.close()
    return out


if __name__ == '__main__':
    fn = sys.argv[1]
    opts = sys.argv[2] if len(sys.argv) > 2 else '+xo'
    maxnodes = int(sys.argv[3]) if len(sys.argv) > 3 else 2000000
    mind = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    frames = {}
    cur = None
    for line in open(fn):
        line = line.rstrip('\n')
        if line.startswith('#'):
            cur = line[1:].strip()
            frames[cur] = []
        elif line.strip() and cur:
            frames[cur].append(line.replace(' ', ''))
    for name, rows in frames.items():
        frame = '\n'.join(rows)
        t = time.time()
        n = 0
        for combo, diag in variants(frame, opts):
            n += 1
            for first, win, kos, pv, dm, nm in analyse(diag, maxnodes):
                if dm >= mind:
                    print('%s|%s|%s first=%s key=%s kos=%s passval=%s depth=%d moves=%d' % (
                        name, combo, diag.replace('\n', '/'), first, win, ','.join(kos), pv, dm, nm), flush=True)
        print('# %s: %d variants in %.1fs' % (name, n, time.time() - t), flush=True)
