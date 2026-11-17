"""Manual tree authoring with solver verification.

Tree text: indented (2 spaces per ply) list of moves in authoring coordinates.
  'db'          a move
  'db RIGHT'    accepted leaf
  'ca *'        wrong solver move: auto-pick refutation (single reply)
  'ca ko'       comment
"""
import sys
sys.path.insert(0, 'scratch')
from tsu import *


def parse_tree(text):
    root = Node()
    stack = [(-1, root)]
    for line in text.split('\n'):
        if not line.strip() or line.strip().startswith('#'):
            continue
        ind = (len(line) - len(line.lstrip(' '))) // 2
        toks = line.split()
        n = Node(toks[0])
        n.auto = False
        for t in toks[1:]:
            if t == 'RIGHT':
                n.right = True
            elif t == '*':
                n.auto = True
            else:
                n.comment = (n.comment + ' ' if n.comment else '') + t
        while stack[-1][0] >= ind:
            stack.pop()
        stack[-1][1].add(n)
        stack.append((ind, n))
    return root


def explore(p, moves=(), best=2, detail=True):
    moves = tuple(moves)
    print(p.show(moves))
    st, v = p.query(list(moves))
    if st:
        print(st)
        return
    solver_to_move = len(moves) % 2 == 0
    print('to move:', 'SOLVER' if solver_to_move else 'OPP', p.colour_at(len(moves)), ' ', p.report(moves))
    if not solver_to_move and detail:
        for r in sorted(v):
            if r == 'pass':
                continue
            st2, v2 = p.query(list(moves + (r,)))
            if st2:
                print('   ', r, st2)
                continue
            wins = [m for m, x in v2.items() if x >= best and m != 'pass']
            kos = [m for m, x in v2.items() if x == 1 and m != 'pass']
            thr = v2.get('pass', 0) < best
            print('   %s %s -> solver wins with: %s%s%s' % (r, 'THREAT' if thr else 'tenuki-ok', ' '.join(sorted(wins)) or 'NONE',
                                                    ' | ko: ' + ' '.join(kos) if (kos and not wins) else '',
                                                    ' (pass ok)' if not thr else ''))


def auto_refutation(p, moves, best=2):
    st, v = p.query(list(moves))
    known = [x for x in v.values() if x >= 0]
    if not known:
        return None
    lo = min(known)
    bestr = None
    for r, x in sorted(v.items()):
        if x != lo or r == 'pass':
            continue
        st2, v2 = p.query(list(moves + (r,)))
        if st2 == 'CAPTURED':
            return r
        if st2:
            continue
        nthr = 0
        for m in v2:
            if m == 'pass':
                continue
            st3, v3 = p.query(list(moves + (r, m)))
            if st3 == 'CAPTURED':
                nthr += 100
            elif not st3 and v3.get('pass', 0) >= best:
                nthr += 1
        if bestr is None or nthr < bestr[0]:
            bestr = (nthr, r)
    return bestr[1] if bestr else None


def verify(p, root, best=2, verbose=True):
    """Returns list of problems (strings). Also fills auto refutations."""
    issues = []
    notes = []

    def solver_children(node, moves, on_right):
        # node's children are solver moves
        st, v = p.query(list(moves))
        if st:
            issues.append('%s: cannot move here (%s)' % (' '.join(moves), st))
            return
        wins = sorted(m for m, x in v.items() if x >= best and m != 'pass')
        listed = [c.move for c in node.children]
        for m, x in sorted(v.items()):
            if x == -1 and m != 'pass' and (on_right or m in listed):
                issues.append('%s: AMBIGUOUS value for solver move %s' % (' '.join(moves) or 'root', m))
        if on_right:
            if not wins:
                issues.append('%s: on right path but solver has no winning move' % ' '.join(moves))
            for m in wins:
                if m not in listed:
                    issues.append('%s: MISSING winning move %s' % (' '.join(moves) or 'root', m))
        for c in node.children:
            mm = moves + (c.move,)
            if c.move not in v:
                issues.append('%s: illegal/unknown solver move' % ' '.join(mm))
                continue
            val = v[c.move]
            if on_right and val >= best:
                opp_children(c, mm, True)
            else:
                if on_right is False and val >= best:
                    issues.append('%s: move in WRONG branch actually wins (val=%d)' % (' '.join(mm), val))
                opp_children(c, mm, False)

    def opp_children(node, moves, on_right):
        st, v = p.query(list(moves))
        if st == 'CAPTURED':
            if on_right:
                if node.children:
                    issues.append('%s: children after capture' % ' '.join(moves))
                if not node.right:
                    issues.append('%s: capture leaf not RIGHT' % ' '.join(moves))
            return
        if st:
            issues.append('%s: %s' % (' '.join(moves), st))
            return
        if on_right:
            if not node.children:
                if not node.right:
                    issues.append('%s: right-path leaf not marked RIGHT' % ' '.join(moves))
                # info: remaining threats
                thr = []
                for r in sorted(v):
                    if r == 'pass':
                        continue
                    st2, v2 = p.query(list(moves + (r,)))
                    if st2:
                        continue
                    if v2.get('pass', 0) < best:
                        wins = [m for m, x in v2.items() if x >= best and m != 'pass']
                        thr.append('%s(%s)' % (r, ','.join(sorted(wins))))
                if thr:
                    notes.append('leaf %s: remaining threats %s' % (' '.join(moves), ' '.join(thr)))
                return
            if node.right:
                issues.append('%s: RIGHT on non-leaf' % ' '.join(moves))
            listed = [c.move for c in node.children]
            thr = []
            for r in sorted(v):
                if r == 'pass' or r in listed:
                    continue
                st2, v2 = p.query(list(moves + (r,)))
                if st2:
                    continue
                if v2.get('pass', 0) < best:
                    wins = [m for m, x in v2.items() if x >= best and m != 'pass']
                    thr.append('%s(%s)' % (r, ','.join(sorted(wins))))
            if thr:
                notes.append('node %s: unlisted threats %s' % (' '.join(moves), ' '.join(thr)))
            for c in node.children:
                if c.move not in v:
                    issues.append('%s: illegal opp move' % ' '.join(moves + (c.move,)))
                    continue
                if v[c.move] < best:
                    issues.append('%s: opp reply actually refutes a "right" move?! (val %d)' % (' '.join(moves + (c.move,)), v[c.move]))
                solver_children(c, moves + (c.move,), True)
        else:
            if node.right:
                issues.append('%s: RIGHT on wrong path' % ' '.join(moves))
            if not node.children:
                if getattr(node, 'auto', False):
                    r = auto_refutation(p, moves, best)
                    if r is None:
                        issues.append('%s: no refutation found' % ' '.join(moves))
                        return
                    c = node.add(Node(r)); c.auto = False
                    if v[r] == 1:
                        c.comment = 'ko'
                else:
                    issues.append('%s: wrong line ends on solver move' % ' '.join(moves))
                    return
            for c in node.children:
                mm = moves + (c.move,)
                if c.move not in v:
                    issues.append('%s: illegal opp move' % ' '.join(mm))
                    continue
                if v[c.move] == -1:
                    issues.append('%s: AMBIGUOUS refutation' % ' '.join(mm))
                    continue
                if v[c.move] >= best:
                    issues.append('%s: reply does NOT refute (solver still wins)' % ' '.join(mm))
                    continue
                st2, v2 = p.query(list(mm))
                if st2 == 'CAPTURED':
                    continue
                if st2:
                    issues.append('%s: %s' % (' '.join(mm), st2))
                    continue
                if v[c.move] == 1 and not c.comment and verbose:
                    notes.append('%s: refutation leads to ko' % ' '.join(mm))
                if not c.children:
                    # info: solver tries that still need answering
                    tries = []
                    for m in sorted(v2):
                        if m == 'pass':
                            continue
                        st3, v3 = p.query(list(mm + (m,)))
                        if st3 == 'CAPTURED':
                            tries.append(m + '!!')
                        elif not st3 and v3.get('pass', 0) >= best:
                            tries.append(m)
                    if tries:
                        notes.append('wrong leaf %s: solver tries needing answer: %s' % (' '.join(mm), ' '.join(tries)))
                solver_children(c, mm, False)

    solver_children(root, (), True)
    return issues, notes


def finalize(p, text, transform='id', shift=(0, 0), swap=False, best=2, quiet=False):
    root = parse_tree(text)
    issues, notes = verify(p, root, best)
    if not quiet:
        for i in issues:
            print('ISSUE:', i)
        for n in notes:
            print('note:', n)
        print('nodes=%d maxdepth=%d' % (count_nodes(root), max_depth(root)))
    sgf = to_sgf(p, root, make_tf(transform, shift))
    if swap:
        sgf = swap_colours(sgf)
    return sgf, issues, root


def swap_colours(sgf):
    out = sgf.replace('AB[', 'A#[').replace('AW[', 'AB[').replace('A#[', 'AW[')
    out = out.replace(';B[', ';#[').replace(';W[', ';B[').replace(';#[', ';W[')
    return out
