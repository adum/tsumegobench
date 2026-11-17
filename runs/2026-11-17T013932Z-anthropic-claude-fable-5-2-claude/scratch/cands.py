from specs import SPECS
C = {}
# --- already clear (auto K=1 trees) ---
C['bb5ko'] = dict(diag=SPECS[9]['diag'], first='B', tf='flipx', kw=dict(K=1))            # was slot 6
C['cut2'] = dict(diag=SPECS[7]['diag'], first='B', tf='rot180', shift=(2,0), kw=dict(K=1))            # was slot 7
C['peep22'] = dict(diag=SPECS[8]['diag'], first='W', tf='flipy', kw=dict(K=1, replies={'ba':'ab ac aa ca'}))                        # was slot 8
# --- new candidates ---
C['g13'] = dict(diag=".X@+++oX./.X@+++oX./.X@@++oX./.XX@@@XX./..XXXXX..", first='B', tf='transpose', shift=(4,0), kw=dict(K=1))
C['c12'] = dict(diag="++++X./+++@X./++x@X./@@@@X./XXXXX.", first='B', tf='rot180', swap=True, kw=dict(K=1))
C['s23'] = dict(diag=".X+x+++X./.X@+++@X./.X@+x@@X./.X@@@@XX./.XXXXXX..", first='W', tf='flipy', shift=(5,0), swap=True, kw=dict(K=1))
C['c15'] = dict(diag="+x+@X./+++@X./++@@X./+@@XX./XXXX..", first='W', tf='tr_flipx', kw=dict(K=1, replies={'bb ad ab':'ac ca bc'}))
C['s37'] = dict(diag=".X++++++X./.X@++x+@X./.X@@@@@@X./.XXXXXXXX.", first='W', tf='tr_flipy', shift=(3,0), swap=True, kw=dict(K=1))
C['c23'] = dict(diag="++++X./+x+@X./+@+@X./@@@@X./XXXXX.", first='B', tf='flipy', kw=dict(K=1))
C['c4'] = dict(diag="+x++@X./++++@X./+@@@@X./XXXXXX.", first='W', tf='id', swap=True, kw=dict(K=1))
C['c84'] = dict(diag="++++@X./+x++@X./+x+@@X./@@@@XX./XXXXX..", first='W', tf='rot180', kw=dict(K=1))
C['e25'] = dict(diag=".X@+++@@X./.X@xx++@X./.X@@@@@@X./.XXXXXXXX.", first='B', tf='tr_flipx', shift=(5,0), kw=dict(K=2))
C['e46'] = dict(diag=".X++++@X./.X@x+x@X./.X@@+@@X./.XX@@@XX./..XXXXX..", first='W', tf='flipy', shift=(6,0), swap=True, kw=dict(K=2))
C['m4'] = dict(diag=".X@@+++X./.X@+++@X./.X@+x@@X./.X@@@@XX./.XXXXXX..", first='B', tf='id', shift=(7,0), swap=True, kw=dict(K=1, replies={'eb':'ga db'}, inner_wrong=1))
C['k83'] = dict(diag="+x+@@X./+x++@X./@@@@@X./XXXXXX.", first='B', tf='tr_flipy', kw=dict(K=2))
C['e28'] = dict(diag=".X@++x@X./.X@@x+@X./.XX@@+@X./..XX@@@X./...XXXXX.", first='W', tf='tr_flipy', shift=(5,0), kw=dict(K=2))
C['k11'] = dict(diag="+x+@X./++@@X./+x@XX./@@@X../XXXX..", first='B', tf='flipx', kw=dict(K=2))
C['h1'] = dict(diag="++++@X./+x++@X./+++@@X./+@@@XX./XXXXX..", first='W', tf='rot180', kw=dict(K=1, follow=1, inner_wrong=2, follow_cap=2, replies={'cb bc ad':'ca cc','cb bc ad ca ba':'aa ac'}, tries={'aa ad':'','cc ab':''}))

FINAL = {1:'e46', 2:'e28', 3:'m4', 4:'cut2', 5:'bb5ko', 6:'c15', 7:'peep22', 8:'s23', 9:'c12', 10:'h1'}
C['s20'] = dict(diag="..X@+xx+X./..X@+++@X./..X@@+@@X./..XX@@@XX./...XXXXX..", first='W', tf='id', shift=(5,0), swap=True, kw=dict(K=1))
FINAL[3] = 's20'
