"""Independent structural check of output SGFs (fresh minimal implementation)."""
import re
import sys

N = 19


def parse(text):
    assert text.startswith('(;') and text.endswith(')'), 'must start with (; and end with )'
    pos = 0

    def node():
        nonlocal pos
        assert text[pos] == ';'
        pos += 1
        props = []
        while pos < len(text) and text[pos].isupper():
            m = re.match(r'[A-Z]+', text[pos:])
            k = m.group(0)
            pos += len(k)
            vals = []
            while pos < len(text) and text[pos] == '[':
                j = pos + 1
                v = ''
                while text[j] != ']':
                    if text[j] == '\\':
                        j += 1
                    v += text[j]
                    j += 1
                vals.append(v)
                pos = j + 1
            props.append((k, vals))
        return {'props': props, 'children': []}

    def tree():
        nonlocal pos
        assert text[pos] == '('
        pos += 1
        first = cur = None
        while text[pos] == ';':
            n = node()
            if first is None:
                first = n
            else:
                cur['children'].append(n)
            cur = n
        while text[pos] == '(':
            cur['children'].append(tree())
        assert text[pos] == ')'
        pos += 1
        return first

    t = tree()
    assert pos == len(text), 'trailing data'
    return t


def xy(s):
    return ord(s[0]) - 97, ord(s[1]) - 97


def neighbors(x, y):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = x + dx, y + dy
        if 0 <= a < N and 0 <= b < N:
            yield a, b


def group(board, x, y):
    c = board[(x, y)]
    seen = {(x, y)}
    libs = set()
    st = [(x, y)]
    while st:
        p = st.pop()
        for q in neighbors(*p):
            v = board.get(q)
            if v == c and q not in seen:
                seen.add(q)
                st.append(q)
            elif v is None:
                libs.add(q)
    return seen, libs


def play(board, ko, x, y, c):
    if (x, y) in board:
        raise ValueError('occupied')
    if ko == (x, y):
        raise ValueError('ko')
    b = dict(board)
    b[(x, y)] = c
    o = 'W' if c == 'B' else 'B'
    caps = []
    for q in neighbors(x, y):
        if b.get(q) == o:
            g, l = group(b, *q)
            if not l:
                for s in g:
                    del b[s]
                caps += list(g)
    g, l = group(b, x, y)
    if not l:
        raise ValueError('suicide')
    newko = caps[0] if (len(caps) == 1 and len(g) == 1 and len(l) == 1) else None
    return b, newko


def check(fn):
    text = open(fn, encoding='utf-8').read()
    errs = []
    if text != text.strip():
        errs.append('leading/trailing whitespace')
    root = parse(text.strip())
    rp = dict(root['props'])
    keys = [k for k, v in root['props']]
    if rp.get('SZ') != ['19']:
        errs.append('SZ')
    if 'AB' not in rp or 'AW' not in rp:
        errs.append('AB/AW')
    if 'B' in rp or 'W' in rp or 'C' in rp:
        errs.append('root move/comment')
    board = {}
    for k in ('AB', 'AW'):
        for v in rp.get(k, []):
            if xy(v) in board:
                errs.append('dup setup')
            board[xy(v)] = 'B' if k == 'AB' else 'W'
    for p in list(board):
        g, l = group(board, *p)
        if not l:
            errs.append('setup group without liberties')
    firsts = set()
    stats = {'nodes': 1, 'maxlen': 0, 'rights': 0}

    def rec(n, b, ko, color, depth):
        for ch in n['children']:
            stats['nodes'] += 1
            props = dict(ch['props'])
            mv = [k for k in ('B', 'W') if k in props]
            if len(mv) != 1:
                errs.append('node move count')
                continue
            c = mv[0]
            if depth == 0:
                firsts.add(c)
            if color and c != color:
                errs.append('alternation')
            v = props[c][0]
            if len(v) != 2:
                errs.append('pass/invalid')
                continue
            try:
                nb, nko = play(b, ko, *xy(v), c)
            except ValueError as e:
                errs.append('illegal %s %s' % (v, e))
                continue
            cm = ''.join(props.get('C', []))
            if 'RIGHT' in cm:
                stats['rights'] += 1
                if ch['children']:
                    errs.append('RIGHT on non-leaf')
            if '<' in cm or '>' in cm:
                errs.append('html')
            stats['maxlen'] = max(stats['maxlen'], depth + 1)
            rec(ch, nb, nko, 'W' if c == 'B' else 'B', depth + 1)

    rec(root, board, None, None, 0)
    if len(firsts) != 1:
        errs.append('first color %s' % firsts)
    if stats['maxlen'] > 14:
        errs.append('line too long')
    if stats['nodes'] > 120:
        errs.append('too many nodes')
    if stats['rights'] < 1:
        errs.append('no RIGHT')
    return errs, stats, firsts


if __name__ == '__main__':
    for fn in sys.argv[1:]:
        errs, stats, firsts = check(fn)
        print(fn, 'first=%s' % ''.join(firsts), stats, 'ERRORS: %s' % errs if errs else 'OK')
