"""Final assembly: build, validate, and (optionally) write all chosen problems.
Usage: python3 final.py [check|write] [problem numbers...]"""
import sys
from build import build
from validate import check

P = {}

# 20-30 kyu: Black to live, corner; block the cutting stone's escape.
P[1] = dict(design='p1a', t=0, shift=(0, 0),
            tree="(;B[dc]C[RIGHT])(;B[da];W[dc])(;B[ba];W[dc])(;B[aa];W[dc])")

# 20-30 kyu: Black to kill, bottom side; connect the first-line stones, then the vital point.
P[2] = dict(design='e61_25', t=2, shift=(3, 0),
            tree="(;B[ea](;W[ga];B[ia]C[RIGHT])(;W[ia];B[ga]C[RIGHT]))"
                 "(;B[ga];W[ea])(;B[ha];W[ea])(;B[ia];W[ea])")

# 10-19 kyu: White to live, right side; connect at the cutting point, two eye areas are miai.
P[3] = dict(design='m21_8c', t=6, shift=(0, 3),
            tree="(;W[fb]"
                 "(;B[fa];W[ga](;B[ia];W[ja]C[RIGHT])(;B[ja];W[ia]C[RIGHT]))"
                 "(;B[ga];W[fa](;B[ia];W[ja]C[RIGHT])(;B[ja];W[ia]C[RIGHT]))"
                 "(;B[ia];W[ja]C[RIGHT])"
                 "(;B[ja];W[ia](;B[fa];W[ga]C[RIGHT])(;B[ga];W[fa]C[RIGHT])))"
                 "(;W[fa];B[fb])(;W[ga];B[fb])(;W[ia];B[fb])(;W[ja];B[fb])")

# 10-19 kyu: Black to kill, left side; first-line placement, capture, connect out.
P[4] = dict(design='c32_3', t=4, shift=(0, 4),
            tree="(;B[fa](;W[ea];B[eb];W[fb];B[ea]C[RIGHT])(;W[eb];B[ea]C[RIGHT])(;W[fb];B[ea]C[RIGHT]))"
                 "(;B[ea];W[fa]C[Ko])(;B[eb];W[fa]C[Ko])(;B[fb];W[fa])(;B[ga];W[fa])(;B[ha];W[fa])")

# 5-9 kyu: Black to kill, bottom-left corner; 2-2 placement and a three-stone sacrifice.
P[5] = dict(design='c32_1b', t=2, shift=(0, 0),
            tree="(;B[bb]"
                 "(;W[ab];B[ba];W[bc];B[ba]C[RIGHT])"
                 "(;W[ba];B[ab];W[bc];B[ab]C[RIGHT])"
                 "(;W[bc](;B[ab];W[ba];B[ab]C[RIGHT])(;B[ba];W[ab];B[ba]C[RIGHT])(;B[db](;W[ab];B[ba]C[RIGHT])(;W[ba];B[ab]C[RIGHT]))))"
                 "(;B[ab];W[bb])(;B[ba];W[bb])(;B[bc];W[bb])(;B[db];W[bb])")

# 5-9 kyu: Black to live, bottom-right corner; against two invading stones.
P[6] = dict(design='m91_4', t=3, shift=(0, 0),
            tree="(;B[bb]"
                 "(;W[ab];B[ba](;W[cb];B[ca](;W[aa];B[cc]C[RIGHT])(;W[cc];B[aa]C[RIGHT]))"
                 "(;W[cc](;B[aa](;W[ca];B[cb]C[RIGHT])(;W[cb];B[ca]C[RIGHT]))(;B[cb]C[RIGHT])))"
                 "(;W[ba];B[ab];W[cb];B[cc]C[RIGHT]))"
                 "(;B[ab];W[bb];B[ba];W[aa]C[Ko])(;B[ba];W[bb];B[ab];W[aa]C[Ko])"
                 "(;B[cc];W[bb])(;B[aa];W[ab])(;B[cb];W[ba])")

# 1-4 kyu: White to live, left side; first-line move, other moves allow only seki or ko.
P[7] = dict(design='wc6', t=4, shift=(0, 4),
            tree="(;W[ga](;B[eb];W[gb]C[RIGHT])(;B[gb];W[eb];B[fa](;W[da]C[RIGHT])(;W[ha](;B[da];W[db]C[RIGHT])(;B[db];W[da]C[RIGHT])))"
                 "(;B[fa](;W[gb]C[RIGHT])(;W[da];B[gb];W[eb]C[RIGHT])(;W[eb];B[gb](;W[da]C[RIGHT])(;W[ha](;B[da];W[db]C[RIGHT])(;B[db];W[da]C[RIGHT])))))"
                 "(;W[da];B[eb]C[Seki])(;W[eb];B[ga]C[Seki])(;W[fa];B[eb]C[Seki])"
                 "(;W[gb];B[ga]C[Seki])(;W[ha];B[da]C[Seki])(;W[db];B[gb]C[Ko])")

# 1-4 kyu: White to kill, top side; placement.
P[8] = dict(design='ek5', t=0, shift=(4, 0), swap=True,
            tree="(;B[fb](;W[ca];B[ea];W[gb];B[fa]C[RIGHT])"
                 "(;W[ea];B[ca](;W[fa];B[gb];W[eb];B[gb]C[RIGHT])(;W[gb];B[fa];W[eb];B[fa]C[RIGHT]))"
                 "(;W[fa];B[ea];W[gb];B[fa]C[RIGHT])"
                 "(;W[gb];B[fa](;W[ca];B[ea]C[RIGHT])(;W[ea];B[ca];W[eb];B[fa]C[RIGHT])(;W[eb](;B[ca];W[ea];B[fa]C[RIGHT])(;B[ea];W[da];B[fa]C[RIGHT]))))"
                 "(;B[ca];W[fa](;B[ea];W[gb])(;B[fb];W[gb]))"
                 "(;B[ea];W[fb](;B[ca];W[da])(;B[da];W[ca]))"
                 "(;B[eb];W[ca](;B[ea];W[fb])(;B[fb];W[ea]))"
                 "(;B[fa];W[ca])"
                 "(;B[gb];W[ca](;B[ea];W[fb]))"
                 "(;B[da];W[ca](;B[ea];W[fb])(;B[fb];W[ea]))")

# about 1 dan: White to kill, top-right corner; first-line move, the tempting kills only give ko.
P[9] = dict(design='wj30', t=1, shift=(0, 0), swap=True,
            tree="(;B[ba](;W[bb];B[db](;W[aa](;B[ab];W[ac];B[bc]C[RIGHT])(;B[ac];W[da];B[ca];W[ba];B[da]C[RIGHT]))"
                 "(;W[ac];B[aa];W[ab](;B[bc]C[RIGHT])(;B[da]C[RIGHT])))(;W[db];B[bb]C[RIGHT]))"
                 "(;B[bb];W[ba]C[Ko])(;B[db];W[ba]C[Ko])(;B[ab];W[ac]C[Ko])"
                 "(;B[aa];W[ab])(;B[bc];W[ba])(;B[ac];W[ba])")

# about 1 dan: White to live, bottom side; choose which half to settle first.
P[10] = dict(design='wc8', t=2, shift=(4, 0),
             tree="(;W[gb]"
                  "(;B[ca];W[da](;B[db];W[eb];B[ea](;W[db]C[RIGHT])(;W[ga]C[RIGHT]))"
                  "(;B[ea];W[db];B[ga](;W[eb](;B[ha];W[hb](;B[fa];W[ga]C[RIGHT])(;B[ga];W[fa]C[RIGHT]))(;B[hb];W[ha]C[RIGHT]))(;W[ha]C[RIGHT])))"
                  "(;B[da];W[eb](;B[ca];W[ea]C[RIGHT])(;B[ea];W[ca];B[ga](;W[db](;B[ha];W[hb]C[RIGHT])(;B[hb];W[ha]C[RIGHT]))(;W[ha]C[RIGHT]))))"
                  "(;W[ca];B[da]C[Seki])(;W[da];B[gb]C[Seki])(;W[eb];B[ea]C[Seki])"
                  "(;W[ea];B[eb]C[Ko])(;W[ga];B[ca]C[Ko])(;W[hb];B[ca]C[Ko])")


def make(n):
    p = P[n]
    return build(p['design'], p['tree'], p['t'], shift=p['shift'], swap=p.get('swap', False))


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    nums = [int(x) for x in sys.argv[2:]] or sorted(P)
    for n in nums:
        sgf, spec = make(n)
        print('==== problem %02d' % n, flush=True)
        print(sgf, flush=True)
        if mode == 'writeonly':
            fn = '../outputs/problem-%02d.sgf' % n
            open(fn, 'w').write(sgf)
            print('written (no validation)', fn)
            continue
        errs = check(sgf, spec, verbose=False)
        print('RESULT', n, 'ERRORS' if errs else 'OK', flush=True)
        if mode == 'write' and not errs:
            fn = '../outputs/problem-%02d.sgf' % n
            old = open(fn).read() if __import__('os').path.exists(fn) else None
            if old != sgf:
                open(fn, 'w').write(sgf)
                print('written', fn)
            else:
                print('unchanged', fn)
