"""Minimal Go board, SGF tools and a local life-and-death solver."""
import sys, re, random

N = 19
EMPTY, BLACK, WHITE = 0, 1, 2
def opp(c): return 3 - c

NEI = []
for i in range(N * N):
    x, y = i % N, i // N
    l = []
    if x > 0: l.append(i - 1)
    if x < N - 1: l.append(i + 1)
    if y > 0: l.append(i - N)
    if y < N - 1: l.append(i + N)
    NEI.append(tuple(l))

def s2i(s):
    return (ord(s[1]) - 97) * N + (ord(s[0]) - 97)
def i2s(i):
    return chr(97 + i % N) + chr(97 + i // N)

ZOB = [[random.Random(k * 3 + c).getrandbits(64) for c in range(3)] for k in range(N * N)]

class Board:
    __slots__ = ('b', 'h')
    def __init__(self, b=None, h=None):
        if b is None:
            self.b = [0] * (N * N); self.h = 0
        else:
            self.b = b; self.h = h
    def copy(self):
        return Board(self.b[:], self.h)
    def set(self, i, c):
        old = self.b[i]
        if old: self.h ^= ZOB[i][old]
        if c: self.h ^= ZOB[i][c]
        self.b[i] = c
    def chain(self, i):
        b = self.b; c = b[i]
        stones = [i]; seen = {i}; libs = set()
        k = 0
        while k < len(stones):
            p = stones[k]; k += 1
            for q in NEI[p]:
                v = b[q]
                if v == c:
                    if q not in seen:
                        seen.add(q); stones.append(q)
                elif v == EMPTY:
                    libs.add(q)
        return stones, libs
    def play(self, i, c):
        """Play; return (captured list) or None if illegal (occupied/suicide)."""
        b = self.b
        if b[i] != EMPTY: return None
        self.set(i, c)
        o = opp(c); cap = []
        for q in NEI[i]:
            if b[q] == o:
                st, lb = self.chain(q)
                if not lb:
                    for s in st: self.set(s, EMPTY)
                    cap.extend(st)
        if not cap:
            st, lb = self.chain(i)
            if not lb:
                self.set(i, EMPTY)
                return None
        return cap

def benson_alive(board, color):
    """Return set of points of chains of `color` that are pass-alive (Benson)."""
    b = board.b
    # chains
    chains = {}; cid = [-1] * (N * N); clist = []
    for i in range(N * N):
        if b[i] == color and cid[i] < 0:
            st, lb = board.chain(i)
            k = len(clist); clist.append((st, lb))
            for s in st: cid[s] = k
    # regions: maximal connected sets of non-color points
    rid = [-1] * (N * N); regions = []
    for i in range(N * N):
        if b[i] != color and rid[i] < 0:
            k = len(regions); pts = [i]; rid[i] = k; j = 0
            while j < len(pts):
                p = pts[j]; j += 1
                for q in NEI[p]:
                    if b[q] != color and rid[q] < 0:
                        rid[q] = k; pts.append(q)
            regions.append(pts)
    alive_chains = set(range(len(clist)))
    live_regions = set(range(len(regions)))
    # region -> adjacent chains; vital relation
    radj = []
    vital = []
    for k, pts in enumerate(regions):
        adj = set()
        for p in pts:
            for q in NEI[p]:
                if b[q] == color: adj.add(cid[q])
        radj.append(adj)
        vs = set()
        empties = [p for p in pts if b[p] == EMPTY]
        for c in adj:
            libs = clist[c][1]
            if all(p in libs for p in empties):
                vs.add(c)
        vital.append(vs)
    while True:
        changed = False
        for c in list(alive_chains):
            n = sum(1 for k in live_regions if c in vital[k])
            if n < 2:
                alive_chains.discard(c); changed = True
        for k in list(live_regions):
            if not radj[k] <= alive_chains:
                live_regions.discard(k); changed = True
        if not changed: break
    res = set()
    for c in alive_chains: res.update(clist[c][0])
    return res

# ---------------- SGF ----------------
class Node:
    def __init__(self, props=None):
        self.props = props or {}
        self.children = []
    def move(self):
        for c in ('B', 'W'):
            if c in self.props: return c, self.props[c][0]
        return None

def parse_sgf(text):
    pos = 0; n = len(text)
    def ws():
        nonlocal pos
        while pos < n and text[pos] in ' \t\r\n': pos += 1
    def parse_tree():
        nonlocal pos
        ws(); assert text[pos] == '(', text[pos:pos+20]; pos += 1
        nodes = []
        ws()
        while pos < n and text[pos] == ';':
            pos += 1
            node = Node()
            ws()
            while pos < n and text[pos].isalpha():
                m = re.match(r'[A-Za-z]+', text[pos:]); key = m.group(0); pos += len(key)
                ws(); vals = []
                while pos < n and text[pos] == '[':
                    pos += 1; v = []
                    while text[pos] != ']':
                        if text[pos] == '\\': pos += 1
                        v.append(text[pos]); pos += 1
                    pos += 1; vals.append(''.join(v)); ws()
                node.props.setdefault(key, []).extend(vals)
            if nodes: nodes[-1].children.append(node)
            nodes.append(node); ws()
        while pos < n and text[pos] == '(':
            sub = parse_tree(); nodes[-1].children.append(sub); ws()
        assert text[pos] == ')'; pos += 1
        return nodes[0]
    return parse_tree()

def write_sgf(root):
    def props(node):
        s = ''
        for k, vs in node.props.items():
            s += k + ''.join('[' + v.replace('\\', '\\\\').replace(']', '\\]') + ']' for v in vs)
        return s
    def rec(node):
        s = ';' + props(node)
        if len(node.children) == 1:
            s += rec(node.children[0])
        elif node.children:
            s += ''.join('\n(' + rec(ch) + ')' for ch in node.children)
        return s
    return '(' + rec(root) + ')\n'

def root_board(root):
    bd = Board()
    for p in root.props.get('AB', []): bd.set(s2i(p), BLACK)
    for p in root.props.get('AW', []): bd.set(s2i(p), WHITE)
    return bd

def show(board, region=None, marks=None):
    xs = [i % N for i in range(N*N) if board.b[i]] + ([i % N for i in region] if region else [])
    ys = [i // N for i in range(N*N) if board.b[i]] + ([i // N for i in region] if region else [])
    x0, x1 = max(0, min(xs) - 1), min(N - 1, max(xs) + 1)
    y0, y1 = max(0, min(ys) - 1), min(N - 1, max(ys) + 1)
    out = ['   ' + ' '.join(chr(97 + x) for x in range(x0, x1 + 1))]
    for y in range(y0, y1 + 1):
        row = []
        for x in range(x0, x1 + 1):
            i = y * N + x
            if marks and i in marks: row.append(marks[i])
            elif board.b[i] == BLACK: row.append('X')
            elif board.b[i] == WHITE: row.append('O')
            elif region and i in region: row.append('.')
            else: row.append(',')
        out.append(' ' + chr(97 + y) + ' ' + ' '.join(row))
    return '\n'.join(out)
