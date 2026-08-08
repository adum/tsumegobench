#!/usr/bin/env python3
"""Minimal Go SGF validator for life-and-death problems."""
import re, sys
from copy import deepcopy

COLS = "abcdefghijklmnopqrs"

def parse_sgf(text):
    text = text.strip()
    assert text.startswith("(;") and text.endswith(")")
    # root props
    body = text[2:-1]
    # extract root until first (; or end of root section
    # Simple recursive descent for trees
    return body

def coords(pt):
    return COLS.index(pt[0]), COLS.index(pt[1])

def neighbors(x, y):
    for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
        nx, ny = x+dx, y+dy
        if 0 <= nx < 19 and 0 <= ny < 19:
            yield nx, ny

class Board:
    def __init__(self):
        self.g = [[None]*19 for _ in range(19)]
    
    def copy(self):
        b = Board()
        b.g = [row[:] for row in self.g]
        return b
    
    def get(self, x, y):
        return self.g[y][x]
    
    def set(self, x, y, c):
        self.g[y][x] = c
    
    def group(self, x, y):
        c = self.get(x, y)
        if c is None:
            return set(), set()
        stones, libs = set(), set()
        stack = [(x,y)]
        seen = set()
        while stack:
            sx, sy = stack.pop()
            if (sx,sy) in seen:
                continue
            seen.add((sx,sy))
            stones.add((sx,sy))
            for nx, ny in neighbors(sx, sy):
                v = self.get(nx, ny)
                if v is None:
                    libs.add((nx,ny))
                elif v == c and (nx,ny) not in seen:
                    stack.append((nx,ny))
        return stones, libs
    
    def play(self, x, y, color):
        if self.get(x,y) is not None:
            raise ValueError(f"occupied {COLS[x]}{COLS[y]}")
        self.set(x,y,color)
        opp = 'W' if color=='B' else 'B'
        captured = []
        for nx, ny in neighbors(x,y):
            if self.get(nx,ny) == opp:
                stones, libs = self.group(nx,ny)
                if not libs:
                    for sx,sy in stones:
                        self.set(sx,sy,None)
                        captured.append((sx,sy))
        stones, libs = self.group(x,y)
        if not libs:
            # suicide - illegal unless capture happened and we have libs now
            # re-check after captures already done
            if not libs:
                raise ValueError(f"suicide {COLS[x]}{COLS[y]} by {color}")
        return captured
    
    def show(self, focus=None):
        lines = []
        for y in range(19):
            row = []
            for x in range(19):
                v = self.get(x,y)
                ch = '.' if v is None else ('X' if v=='B' else 'O')
                row.append(ch)
            lines.append(f"{COLS[y]} " + "".join(row))
        lines.append("  " + "".join(COLS))
        return "\n".join(lines)

def extract_setup_and_tree(sgf):
    sgf = sgf.strip()
    # Find all AB and AW in root - root is before first variation or first move
    # Parse with a simple approach
    i = 0
    assert sgf[0] == '('
    
    def parse_node_sequence(s, idx):
        """Parse from after '(' """
        nodes = []
        while idx < len(s):
            if s[idx] == ';':
                idx += 1
                props = {}
                while idx < len(s) and s[idx] not in '();':
                    # property
                    m = re.match(r'([A-Z]+)((?:\[(?:[^\]]|\\.)*\])*)', s[idx:])
                    if not m:
                        # skip whitespace
                        if s[idx].isspace():
                            idx += 1
                            continue
                        raise ValueError(f"bad prop at {idx}: {s[idx:idx+20]!r}")
                    key = m.group(1)
                    vals = re.findall(r'\[((?:[^\]]|\\.)*)\]', m.group(2))
                    props.setdefault(key, []).extend(vals)
                    idx += m.end()
                nodes.append(props)
            elif s[idx] == '(':
                # variation - collect as children of last node
                children, idx = parse_variations(s, idx)
                if nodes:
                    nodes[-1]['_children'] = nodes[-1].get('_children', []) + children
                else:
                    raise ValueError("variation without node")
            elif s[idx] == ')':
                return nodes, idx
            elif s[idx].isspace():
                idx += 1
            else:
                raise ValueError(f"unexpected {s[idx]!r} at {idx}")
        return nodes, idx
    
    def parse_variations(s, idx):
        vars = []
        while idx < len(s) and s[idx] == '(':
            idx += 1  # skip (
            nodes, idx = parse_node_sequence(s, idx)
            if s[idx] != ')':
                raise ValueError(f"expected ) at {idx}")
            idx += 1
            # skip whitespace
            while idx < len(s) and s[idx].isspace():
                idx += 1
            vars.append(nodes)
        return vars, idx
    
    # whole file is one collection
    idx = 0
    assert sgf[idx] == '('
    idx += 1
    nodes, idx = parse_node_sequence(sgf, idx)
    return nodes

def apply_setup(board, props):
    for pt in props.get('AB', []):
        x,y = coords(pt)
        board.set(x,y,'B')
    for pt in props.get('AW', []):
        x,y = coords(pt)
        board.set(x,y,'W')

def walk(nodes, board, path="", depth=0):
    if not nodes:
        return
    props = nodes[0]
    rest = nodes[1:]
    move = None
    color = None
    if 'B' in props:
        color, move = 'B', props['B'][0]
    elif 'W' in props:
        color, move = 'W', props['W'][0]
    
    if move is not None:
        x,y = coords(move)
        try:
            cap = board.play(x,y,color)
        except ValueError as e:
            print(f"ILLEGAL at {path}/{color}[{move}]: {e}")
            print(board.show())
            return
        comment = props.get('C', [''])[0]
        mark = ' RIGHT' if 'RIGHT' in comment else ''
        cap_s = f" cap={len(cap)}" if cap else ""
        print(f"{'  '*depth}{color}[{move}]{cap_s}{mark}")
    
    children = props.get('_children', [])
    if rest:
        # linear continuation as implicit first child
        walk(rest, board.copy() if children else board, path + f"/{move}", depth+1)
    for i, ch in enumerate(children):
        walk(ch, board.copy(), path + f"/{move}/v{i}", depth+1)

def main(path):
    text = open(path).read().strip()
    # wrap if needed
    if not text.startswith("(;"):
        print("bad start")
        return
    # Our SGFs are (;ROOT ... variations)
    # Make parseable as single tree: wrap moves as children
    # Actually format is (;ROOT(;B..)(;B..)) so after root node come variations
    nodes = extract_setup_and_tree(text)
    root = nodes[0]
    board = Board()
    apply_setup(board, root)
    print(f"=== {path} ===")
    print(board.show())
    # remaining linear + children
    rest = nodes[1:]
    children = root.get('_children', [])
    if rest:
        walk(rest, board.copy(), "main", 0)
    for i, ch in enumerate(children):
        walk(ch, board.copy(), f"v{i}", 0)
    # count RIGHT
    rights = len(re.findall(r'RIGHT', text))
    print(f"RIGHT markers: {rights}")

if __name__ == '__main__':
    for p in sys.argv[1:]:
        main(p)
