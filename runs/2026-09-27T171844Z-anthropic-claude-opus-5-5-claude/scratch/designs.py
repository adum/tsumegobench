from gotools import BLACK, WHITE

D = {}

# P1 draft: black to live; block the cutting stone's escape (atari from the correct side)
D['p1a'] = dict(
    rows=[
        "..x.xxW",
        "xxxOxW-",
        "OOx.xW-",
        "-OOOWW-",
    ],
    att=WHITE, first=BLACK, solver=BLACK, objective='live',
)

# P2 drafts: white to kill, easy
D['p2a'] = dict(
    rows=[
        "Wx....-",
        "Wxxxxx.",
        "WWWWWWW",
    ],
    att=WHITE, first=WHITE, solver=WHITE, objective='kill',
    target=['bb', 'cb', 'db', 'eb', 'fb', 'ba'],
)
D['p2b'] = dict(
    rows=[
        "W.x...xW",
        "Wxxx.xxW",
        "WWWxxxWW",
        "--WWWW--",
    ],
    att=WHITE, first=WHITE, solver=WHITE, objective='kill',
    target=['cb', 'bb', 'db', 'fb', 'gb'],
)
D['p2c'] = dict(
    rows=[
        "Wx.....W",
        "WxxxxxWW",
        "WWWWWWW-",
    ],
    att=WHITE, first=WHITE, solver=WHITE, objective='kill',
    target=['bb', 'cb', 'db', 'eb', 'fb', 'ba'],
)
D['p2d'] = dict(
    rows=[
        "-Wx....x.W-",
        "-WxxxxxOWW-",
        "-WWWWWWWW--",
    ],
    att=WHITE, first=WHITE, solver=WHITE, objective='kill',
    target=['cb', 'db', 'eb', 'fb', 'gb', 'ca'],
)
D['p2e'] = dict(
    rows=[
        "-Wx...x.W-",
        "-WxxxxOWW-",
        "-WWWWWWW--",
    ],
    att=WHITE, first=WHITE, solver=WHITE, objective='kill',
    target=['cb', 'db', 'eb', 'fb', 'ca'],
)

# mined seed12 #3: white to live
D['m12_3'] = dict(
    rows=[
        "...oB",
        ".o..B",
        "ooooB",
        "BBBBB",
    ],
    att=BLACK, first=WHITE, solver=WHITE, objective='live',
)

# crisp32 #1: black to kill, 1-1 stone + 2-2 placement
D['c32_1'] = dict(
    rows=[
        "X.ooB",
        "..o.B",
        "..oBB",
        "oooB-",
        "BBBB-",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
)

D['c32_1b'] = dict(
    rows=[
        "X.ooB",
        "..o.B",
        "o.oBB",
        "oooB-",
        "BBBB-",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
)

D['c32_6'] = dict(
    rows=[
        "...oB",
        "...oB",
        ".ooBB",
        "ooBB-",
        "BBB--",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
)

# base: white 2nd-line group with 3 eyes on first line; black to kill after mutations
D['b_eye3'] = dict(
    rows=[
        "BO.OO.O.OB",
        "BOOOOOOOOB",
        "BBBBBBBBBB",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
    target=['bb', 'cb', 'db', 'eb', 'fb', 'gb', 'hb', 'ib'],
)

D['e61_17'] = dict(
    rows=[
        "--WOX..X.xW",
        "--WXXX...xW",
        "--WWWWxxxxW",
        "-----WWWWWW",
    ],
    att=WHITE, first=WHITE, solver=WHITE, objective='kill',
)
D['e61_17b'] = dict(
    rows=[
        "--WOX....xW",
        "--WXXX...xW",
        "--WWWWxxxxW",
        "-----WWWWWW",
    ],
    att=WHITE, first=WHITE, solver=WHITE, objective='kill',
)
D['e61_5'] = dict(
    rows=[
        "--BX...oB",
        "--Bo.o.oB",
        "--BoooooB",
        "--BBBBBBB",
    ],
    att=BLACK, first=WHITE, solver=WHITE, objective='live',
)
D['e61_25'] = dict(
    rows=[
        "--BX.X....oB",
        "--BooooooooB",
        "--BBBBBBBBBB",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
)
D['e61_51'] = dict(
    rows=[
        "...XW",
        ".xx.W",
        "xx.WW",
        "WWWW-",
    ],
    att=WHITE, first=BLACK, solver=BLACK, objective='live',
)
D['m71_4'] = dict(
    rows=[
        "--Bo.X.oB",
        "--Bo...oB",
        "--BoooooB",
        "--BBBBBBB",
    ],
    att=BLACK, first=WHITE, solver=WHITE, objective='live',
)

# hill-climb bases
D['h1'] = dict(rows=[
    "...oB-",
    "...oB-",
    "ooooB-",
    "BBBBB-",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['h2'] = dict(rows=[
    "-Wx.....xW",
    "-Wx.....xW",
    "-WxxxxxxxW",
    "-WWWWWWWWW",
], att=WHITE, first=WHITE, solver=WHITE, objective='kill')
D['h3'] = dict(rows=[
    "....xW-",
    "...xxW-",
    "..xxWW-",
    "xxxW---",
    "WWWW---",
], att=WHITE, first=WHITE, solver=WHITE, objective='kill')
D['h4'] = dict(rows=[
    ".....oB-",
    ".....oB-",
    "..ooooB-",
    "oooBBBB-",
    "BBBB----",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['h5'] = dict(rows=[
    "....oB-",
    "....oB-",
    "...ooB-",
    "oooo.B-",
    "BBBBBB-",
], att=BLACK, first=WHITE, solver=WHITE, objective='live')
D['h6'] = dict(rows=[
    "-Bo......oB",
    "-Bo......oB",
    "-BooooooooB",
    "-BBBBBBBBBB",
], att=BLACK, first=WHITE, solver=WHITE, objective='live')

D['s6'] = dict(rows=[
    "-B........B",
    "-B.oooooo.B",
    "-BBBBBBBBBB",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')

# handcrafted corner attempts (black to live)
D['k1'] = dict(rows=[
    "......-",
    "...xW.-",
    "..x.W.-",
    ".xxW..-",
    ".WW...-",
    "......-",
], att=WHITE, first=BLACK, solver=BLACK, objective='live')
D['k2'] = dict(rows=[
    "....WW-",
    "...xW--",
    "..x.W--",
    ".xxW---",
    "WWW----",
], att=WHITE, first=BLACK, solver=BLACK, objective='live')
D['k3'] = dict(rows=[
    "...O.W-",
    "...xW--",
    "..x.W--",
    ".xxW---",
    "WWW----",
], att=WHITE, first=BLACK, solver=BLACK, objective='live')
D['k4'] = dict(rows=[
    "...O.W-",
    "...xW--",
    "..x.W--",
    ".xxW---",
    "O.W----",
    "WW-----",
], att=WHITE, first=BLACK, solver=BLACK, objective='live')

D['s6d'] = dict(rows=[
    "-B.o......B",
    "-B.oooooo.B",
    "-BBBBBBBBBB",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['s6e'] = dict(rows=[
    "-B.o.....B-",
    "-B.ooooooB-",
    "-BBBBBBBBB-",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['s5d'] = dict(rows=[
    "-B.o.....B",
    "-B.ooooo.B",
    "-BBBBBBBBB",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')

D['cb1'] = dict(rows=[
    "....oB",
    "....oB",
    "..oooB",
    "oooBBB",
    "BBBB--",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['cb2'] = dict(rows=[
    "...xW",
    "...xW",
    "..xxW",
    "xxxWW",
    "WWWW-",
], att=WHITE, first=WHITE, solver=WHITE, objective='kill')
D['cb4'] = dict(rows=[
    "-B.o...o.B",
    "-B.o...oB-",
    "-Boooooo B-".replace(' ', ''),
    "-BBBBBBBB-",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['cb5'] = dict(rows=[
    "...xW",
    "...xW",
    "..xxW",
    "xxxWW",
    "WWWW-",
], att=WHITE, first=BLACK, solver=BLACK, objective='live')
D['m21_8'] = dict(
    rows=[
        "--BO...X..XB",
        "--BOO.oooooB",
        "--BBBOBBBBBB",
        "----BBB-----",
    ],
    att=BLACK, first=WHITE, solver=WHITE, objective='live',
)
D['c31_6'] = dict(
    rows=[
        ".X.xW",
        ".O.xW",
        "xxxxW",
        "WWWWW",
    ],
    att=WHITE, first=WHITE, solver=WHITE, objective='kill',
)
D['m21_8b'] = dict(
    rows=[
        "--BO...X..XB",
        "--BOO.oooooB",
        "--BBBBBBBBBB",
        "----BBB-----",
    ],
    att=BLACK, first=WHITE, solver=WHITE, objective='live',
)
D['m21_8c'] = dict(
    rows=[
        "--BO...X..XB",
        "--BOO.oooooB",
        "--BBBBBBBBBB",
    ],
    att=BLACK, first=WHITE, solver=WHITE, objective='live',
)
D['m21_2'] = dict(
    rows=[
        "--WO.....X.XW",
        "--Wxxxx...XXW",
        "--WWWWWOXXWWW",
        "------WWWWW--",
    ],
    att=WHITE, first=BLACK, solver=BLACK, objective='live',
)
D['m21_4'] = dict(
    rows=[
        "--BO.......XB",
        "--BOO..ooooXB",
        "--BBBOOBBBBBB",
        "----BBBB-----",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
)
D['c32_3'] = dict(
    rows=[
        "--BX.....oB",
        "--Bo..ooooB",
        "--BooooBBBB",
        "--BBBBBB---",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
)

D['sc1'] = dict(rows=[
    "-Wx...x....W-",
    "-Wxxxxxxx.xW-",
    "-WWWWWWWWWWW-",
], att=WHITE, first=WHITE, solver=WHITE, objective='kill')
D['m91_2'] = dict(
    rows=[
        "--BO.X...oB",
        "--BOO.o..oB",
        "--BBBoooooB",
        "----BBBBBBB",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
)

D['wc1'] = dict(rows=[
    "-BoX..X.oB-",
    "-Bo....ooB-",
    "-BoooooooB-",
    "-BBBBBBBBB-",
], att=BLACK, first=WHITE, solver=WHITE, objective='live')

D['wc6'] = dict(rows=[
    "-Bo.X...oB-",
    "-Bo..X.ooB-",
    "-BoooooooB-",
    "-BBBBBBBBB-",
], att=BLACK, first=WHITE, solver=WHITE, objective='live')
D['m91_9'] = dict(
    rows=[
        "--BO.....XB",
        "--BO.oooooB",
        "--BOOBBBBBB",
        "--BBBB-----",
    ],
    att=BLACK, first=BLACK, solver=BLACK, objective='kill',
)
D['m91_4'] = dict(
    rows=[
        "...xW",
        "...xW",
        "OO.xW",
        "xxxxW",
        "WWWWW",
    ],
    att=WHITE, first=BLACK, solver=BLACK, objective='live',
)

D['wc11'] = dict(rows=[
    "-Bo...X.oB-",
    "-Boo.X..oB-",
    "-BoooooooB-",
    "-BBBBBBBBB-",
], att=BLACK, first=WHITE, solver=WHITE, objective='live')

D['wc8'] = dict(rows=[
    "-B...X..oB-",
    "-Bo..X..oB-",
    "-BoooooooB-",
    "-BBBBBBBBB-",
], att=BLACK, first=WHITE, solver=WHITE, objective='live')

# WG seki candidates (white to live; best = seki)
D['sk21'] = dict(rows=[
    "...ooB",
    "X.X.oB",
    "oooooB",
    "BBBBBB",
], att=BLACK, first=WHITE, solver=WHITE, objective='seki')
D['sk13'] = dict(rows=[
    "O.X.oB",
    "X...oB",
    "oooooB",
    "BBBBBB",
], att=BLACK, first=WHITE, solver=WHITE, objective='seki')
D['sk42'] = dict(rows=[
    "X...oB",
    "OXX.oB",
    "oooooB",
    "BBBBBB",
], att=BLACK, first=WHITE, solver=WHITE, objective='seki')
D['wg3'] = dict(rows=[
    "..X.oB",
    "....oB",
    "oooooB",
    "BBBBBB",
], att=BLACK, first=WHITE, solver=WHITE, objective='live')
D['wg15k'] = dict(rows=[
    ".X..oB",
    "OX..oB",
    "oooooB",
    "BBBBBB",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')

D['s2'] = dict(rows=[
    "....oB",
    "...ooB",
    "ooooBB",
    "BBBB--",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['s2h'] = dict(rows=[
    "X...oB",
    "...ooB",
    "ooooBB",
    "BBBB--",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['wj30'] = dict(rows=[
    "..XOB",
    "..o.B",
    "..ooB",
    "oooBB",
    "BBBB-",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['wj36'] = dict(rows=[
    "..XOB",
    "...OB",
    ".oo.B",
    "oooBB",
    "BBBB-",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['wj33'] = dict(rows=[
    ".O.OB",
    ".X..B",
    "..ooB",
    "oooBB",
    "BBBB-",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
D['ek5'] = dict(rows=[
    "-B....XoB-",
    "-BoO...oB-",
    "-BooooooB-",
    "-BBBBBBBB-",
], att=BLACK, first=BLACK, solver=BLACK, objective='kill')
