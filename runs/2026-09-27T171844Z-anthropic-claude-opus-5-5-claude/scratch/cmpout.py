import final
for n in sorted(final.P):
    sgf, spec = final.make(n)
    cur = open('../outputs/problem-%02d.sgf' % n).read()
    print(n, final.P[n]['design'], 'same-as-current-file' if sgf == cur else 'DIFFERENT', sgf.count(';') - 1, 'nodes')
