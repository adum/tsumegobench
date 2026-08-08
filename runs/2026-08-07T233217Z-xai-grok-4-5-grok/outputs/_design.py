#!/usr/bin/env python3
"""Board designer / liberty checker for tsumego authoring."""
COLS = "abcdefghijklmnopqrs"

class Board:
    def __init__(self):
        self.g = [[None]*19 for _ in range(19)]

    def copy(self):
        b = Board()
        b.g = [row[:] for row in self.g]
        return b

    def place(self, color, pts):
        for p in pts:
            x, y = COLS.index(p[0]), COLS.index(p[1])
            if self.g[y][x] is not None:
                raise ValueError(f"overlap {p}")
            self.g[y][x] = color

    def get(self, x, y):
        return self.g[y][x]

    def neighbors(self, x, y):
        for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
            nx, ny = x+dx, y+dy
            if 0 <= nx < 19 and 0 <= ny < 19:
                yield nx, ny

    def group(self, x, y):
        c = self.get(x, y)
        if c is None:
            return set(), set()
        stones, libs = set(), set()
        stack = [(x,y)]; seen=set()
        while stack:
            sx,sy = stack.pop()
            if (sx,sy) in seen: continue
            seen.add((sx,sy)); stones.add((sx,sy))
            for nx,ny in self.neighbors(sx,sy):
                v = self.get(nx,ny)
                if v is None: libs.add((nx,ny))
                elif v == c and (nx,ny) not in seen: stack.append((nx,ny))
        return stones, libs

    def play(self, color, pt):
        x, y = COLS.index(pt[0]), COLS.index(pt[1])
        if self.get(x,y) is not None:
            raise ValueError(f"occupied {pt}")
        self.g[y][x] = color
        opp = 'W' if color=='B' else 'B'
        captured = []
        for nx,ny in self.neighbors(x,y):
            if self.get(nx,ny)==opp:
                stones, libs = self.group(nx,ny)
                if not libs:
                    for sx,sy in stones:
                        self.g[sy][sx] = None
                        captured.append(COLS[sx]+COLS[sy])
        stones, libs = self.group(x,y)
        if not libs:
            raise ValueError(f"suicide {pt}")
        return captured

    def status(self, region=None):
        seen=set(); out=[]
        for y in range(19):
            for x in range(19):
                if (x,y) in seen: continue
                c = self.get(x,y)
                if c is None: continue
                stones, libs = self.group(x,y)
                seen |= stones
                pts = sorted(COLS[sx]+COLS[sy] for sx,sy in stones)
                lpts = sorted(COLS[lx]+COLS[ly] for lx,ly in libs)
                out.append((c, len(stones), len(libs), pts, lpts))
        return out

    def show(self, xmin=0, xmax=12, ymin=0, ymax=12):
        lines=[]
        for y in range(ymin, ymax+1):
            row=[]
            for x in range(xmin, xmax+1):
                v = self.get(x,y)
                row.append('.' if v is None else ('X' if v=='B' else 'O'))
            lines.append(f"{COLS[y]} " + " ".join(row))
        lines.append("  " + " ".join(COLS[x] for x in range(xmin,xmax+1)))
        return "\n".join(lines)


def make(ab, aw, region=(0,10,0,10), title=""):
    b = Board()
    b.place('B', ab)
    b.place('W', aw)
    if title:
        print("="*50, title)
    print(b.show(*region))
    print("--- groups ---")
    for c,n,l,pts,lpts in b.status():
        print(f"  {c}: {n}st {l}lib stones={pts} libs={lpts}")
    return b


def try_seq(ab, aw, moves, region):
    """moves = [('B','fs'), ('W','ds'), ...]"""
    b = Board(); b.place('B', ab); b.place('W', aw)
    print("SEQ:", moves)
    for color, pt in moves:
        try:
            cap = b.play(color, pt)
            print(f"  {color}[{pt}] cap={cap}")
        except Exception as e:
            print(f"  ILLEGAL {color}[{pt}]: {e}")
            return None
    print(b.show(*region))
    for c,n,l,pts,lpts in b.status():
        print(f"  {c}: {n}st {l}lib stones={pts} libs={lpts}")
    return b


# ============================================================
# P1 (20-30k): Black kills white three-space eye shape on side
# by playing the vital point - NOT classic "three in a row on edge"
# Shape: white has a bent group with one real eye and a false-eye threat
# ============================================================

# Bottom edge, unique bent shape:
#    c d e f g h
# p  X X X X X X
# q  X O O O O X
# r  X O . . O X
# s  . O . O . X
#
# White: cq? no
# White stones: dq,eq,fq,gq, dr, gr, ds, fs
# Actually:
# White: dq eq fq gq | dr gr | ds fs  - hmm connected?
# dq-eq-fq-gq-dr, gr connected via gq, ds via dr, fs via? fs-eq? no fs-fr empty, fs-fq yes!
# Yes connected.

ab1 = ['cp','dp','ep','fp','gp','hp',
       'cq','hq',
       'cr','hr',
       'hs',
       'ip','iq','ir']  # right wall
aw1 = ['dq','eq','fq','gq',
       'dr','gr',
       'ds','fs']

make(ab1, aw1, (2,9,14,18), "P1 setup")
print("\nB[er] kill?")
try_seq(ab1, aw1, [('B','er')], (2,9,14,18))
print("\nB[es] ?")
try_seq(ab1, aw1, [('B','es')], (2,9,14,18))
print("\nB[fr] ?")
try_seq(ab1, aw1, [('B','fr')], (2,9,14,18))
print("\nB[gs] ?")
try_seq(ab1, aw1, [('B','gs')], (2,9,14,18))
print("\nB[cs] ?")
try_seq(ab1, aw1, [('B','cs')], (2,9,14,18))
print("\nAfter B[er], W[fr]?")
try_seq(ab1, aw1, [('B','er'),('W','fr')], (2,9,14,18))
print("\nAfter B[er], W[es]?")
try_seq(ab1, aw1, [('B','er'),('W','es')], (2,9,14,18))
print("\nAfter B[er], W[fr], B[es]?")
try_seq(ab1, aw1, [('B','er'),('W','fr'),('B','es')], (2,9,14,18))
print("\nAfter B[er], W[fr], B[gs]?")
try_seq(ab1, aw1, [('B','er'),('W','fr'),('B','gs')], (2,9,14,18))
