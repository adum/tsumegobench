import sys
from gotools import *


def bbox(b):
    xs = [i % N for i in range(N * N) if b.b[i]]
    ys = [i // N for i in range(N * N) if b.b[i]]
    return max(0, min(xs) - 1), max(0, min(ys) - 1), min(18, max(xs) + 1), min(18, max(ys) + 1)


if __name__ == '__main__':
    for fn in sys.argv[1:]:
        root = parse_sgf(open(fn).read())
        b = board_from_sgf_root(root)
        x0, y0, x1, y1 = bbox(b)
        print(fn)
        print(b.show(x0, y0, x1, y1))
        print()
