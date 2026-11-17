import sys; sys.path.insert(0,'scratch')
from build import *
def tdump(node, indent=0, out=None):
    out = out if out is not None else []
    for c in node.children:
        out.append('  '*indent + c.move + (' RIGHT' if c.right else '') + (' '+c.comment if c.comment else ''))
        tdump(c, indent+1, out)
    return out
def dr(diag, first, **kw):
    diag=diag.replace('/','\n').replace(' ','')
    p=Problem(diag, defender='W', first=first, maxnodes=8000000)
    print(p.show()); print('ROOT', first, p.report())
    b=B2(p, **kw); root=b.build()
    issues,notes=verify(p, root)
    print('\n'.join(tdump(root)))
    for i in issues: print('ISSUE:', i)
    print('nodes=%d maxdepth=%d'%(count_nodes(root), max_depth(root)))
    p.close()
if __name__=='__main__':
    kw=eval('dict(%s)'%sys.argv[3]) if len(sys.argv)>3 else {}
    dr(sys.argv[1], sys.argv[2], **kw)
