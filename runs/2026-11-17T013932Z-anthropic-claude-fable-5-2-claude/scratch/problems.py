from specs import SPECS
PROBLEMS = {}

PROBLEMS[1] = dict(diag=SPECS[1]['diag'], first='W', tf='flipy', shift=(4,0), swap=True, tree="""
ea
  eb
    fb RIGHT
    ga
      da
    da
      fb
da
  ea
eb
  ea
fb
  ea
ga
  ea
""")

PROBLEMS[2] = dict(diag=SPECS[2]['diag'], first='B', tf='tr_flipx', shift=(5,0), tree="""
eb
  db
    fa RIGHT
    fb RIGHT
    da RIGHT
  fb
    da RIGHT
    db RIGHT
    fa RIGHT
da
  eb
db
  eb
fa
  eb
fb
  eb
""")

PROBLEMS[3] = dict(diag=SPECS[3]['diag'], first='B', tf='id', shift=(6,0), swap=True, tree="""
ea
  da
    eb
      db
        ca
          fa
            ea RIGHT
            eb RIGHT
      fa
        ca
          db
            ea RIGHT
            eb RIGHT
      ca
        db RIGHT
        fa RIGHT
    ca
      eb
    db
      eb
  eb
    da RIGHT
    ca
      da
    db
      da
ca
  ea
    da
      db
    db
      da
da
  ea
    ca
      db
    db
      ca
db
  ea
    ca
      da
    da
      ca
eb
  ea
fa
  ea
""")

PROBLEMS[4] = dict(diag=SPECS[4]['diag'], first='W', tf='transpose', shift=(3,0), swap=True, kw=dict(K=1))
PROBLEMS[5] = dict(diag=SPECS[5]['diag'], first='B', tf='rot180', kw=dict(K=1))
PROBLEMS[6] = dict(diag=SPECS[9]['diag'], first='B', tf='flipx', swap=True, kw=dict(K=1))
PROBLEMS[7] = dict(diag=SPECS[7]['diag'], first='B', tf='rot180', shift=(2,0), kw=dict(K=1))
PROBLEMS[8] = dict(diag=SPECS[8]['diag'], first='W', tf='flipy', kw=dict(K=1))
PROBLEMS[9] = dict(diag="++++++X/+++@@@X/+@@@XXX/XXXXX..", first='B', tf='transpose', kw=dict(K=1, follow=0))
PROBLEMS[10] = dict(diag=SPECS[10]['diag'], first='W', tf='tr_flipx', swap=True, kw=dict(K=1, follow=0))

PROBLEMS[1] = dict(diag="+x++@X/+@@@@X/@@XXXX/@@X.../XXX...", first='W', tf='rot180', swap=True, kw=dict(K=1))
