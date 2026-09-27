// df-pn tsumego solver. OR player = attacker (proof = attacker kills), AND player = defender.
// Board 19x19 embedded in 21x21 with EDGE border. Index = (y+1)*21 + (x+1).
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define N 19
#define WD 21
#define SZ (WD*WD)
#define EMPTY 0
#define BLACK 1
#define WHITE 2
#define EDGE 3
#define PASSMOVE 0
#define INF 0x3FFFFFFFu
#define MAXD 160
#define MAXMV 64

static const int D4[4] = {1, -1, WD, -WD};

static uint8_t g_region[SZ], g_safe[SZ], g_target[SZ], g_inbox[SZ];
static int g_regionlist[SZ], g_nregion;
static int g_boxlist[SZ], g_nbox;
static int g_targetlist[SZ], g_ntarget;
static int g_att, g_def, g_kowin, g_strict;
static long long g_nodes, g_maxnodes;
static int g_aborted, g_depthhits, g_def_has_safe, g_cyclehits;

static uint64_t zob[3][SZ], zob_side, zob_ko[SZ], zob_pass, zob_settings;

typedef struct {
    uint8_t b[SZ];
    int ko;
    int lastpass;
    uint64_t hash;
} State;

typedef struct {
    uint64_t key;
    uint32_t pn, dn;
} TTE;

#define TTBITS 22
#define TTSIZE (1u << TTBITS)
static TTE *tt = NULL;

static uint64_t path[MAXD + 8];
static int pathlen;

static uint64_t rng_state = 0x9E3779B97F4A7C15ULL;
static uint64_t rng(void) {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state * 0x2545F4914F6CDD1DULL;
}

static int inited = 0;
static void init_zobrist(void) {
    if (inited) return;
    inited = 1;
    for (int c = 0; c < 3; c++)
        for (int p = 0; p < SZ; p++) zob[c][p] = rng();
    zob_side = rng();
    for (int p = 0; p < SZ; p++) zob_ko[p] = rng();
    zob_pass = rng();
    tt = (TTE *)calloc(TTSIZE, sizeof(TTE));
}

static int gmark[SZ], ggen = 1;
static int lmark[SZ], lgen = 1;

static int get_chain(const uint8_t *b, int p, int *out, int *nl, int *sf, int *lib1) {
    int c = b[p];
    int n = 0, head = 0, libs = 0, s = 0;
    ggen++;
    lgen++;
    out[n++] = p;
    gmark[p] = ggen;
    while (head < n) {
        int q = out[head++];
        if (g_safe[q]) s = 1;
        for (int d = 0; d < 4; d++) {
            int r = q + D4[d];
            if (b[r] == c) {
                if (gmark[r] != ggen) { gmark[r] = ggen; out[n++] = r; }
            } else if (b[r] == EMPTY && lmark[r] != lgen) {
                lmark[r] = lgen;
                libs++;
                if (lib1) *lib1 = r;
            }
        }
    }
    *nl = libs;
    *sf = s;
    return n;
}

static int play(State *s, int p, int c, int *cap_target) {
    int stones[SZ];
    int nl, sf;
    *cap_target = 0;
    int o = 3 - c;
    if (s->b[p] != EMPTY || !g_region[p]) return 0;
    if (p == s->ko && c != g_kowin) return 0;
    s->b[p] = (uint8_t)c;
    s->hash ^= zob[c][p];
    int ncap = 0, lastcap = 0;
    for (int d = 0; d < 4; d++) {
        int q = p + D4[d];
        if (s->b[q] == o) {
            int n = get_chain(s->b, q, stones, &nl, &sf, NULL);
            if (nl == 0 && !sf) {
                for (int i = 0; i < n; i++) {
                    int r = stones[i];
                    if (g_target[r] && o == g_def) *cap_target = 1;
                    s->b[r] = EMPTY;
                    s->hash ^= zob[o][r];
                }
                ncap += n;
                lastcap = stones[0];
            }
        }
    }
    int n = get_chain(s->b, p, stones, &nl, &sf, NULL);
    if (nl == 0 && !sf) return 0;
    if (ncap == 1 && n == 1 && nl == 1) s->ko = lastcap; else s->ko = 0;
    s->lastpass = 0;
    return 1;
}

static int chain_id[SZ], region_id[SZ];
static int bstack[SZ];
#define MAXCH 128
#define MAXRG 128
static int b_nempty[MAXRG];
static uint8_t b_adj[MAXRG][MAXCH];
static int b_cnt[MAXRG][MAXCH];
static uint8_t b_alive[MAXCH], b_rok[MAXRG];

static int benson_targets_alive(const uint8_t *b) {
    int nch = 0, nrg = 0;
    for (int k = 0; k < g_nbox; k++) { int p = g_boxlist[k]; chain_id[p] = -1; region_id[p] = -1; }
    for (int k = 0; k < g_nbox; k++) {
        int p = g_boxlist[k];
        if (b[p] == g_def && chain_id[p] < 0) {
            if (nch >= MAXCH) return 0;
            int sp = 0;
            bstack[sp++] = p;
            chain_id[p] = nch;
            while (sp) {
                int q = bstack[--sp];
                for (int d = 0; d < 4; d++) {
                    int r = q + D4[d];
                    if (g_inbox[r] && b[r] == g_def && chain_id[r] < 0) { chain_id[r] = nch; bstack[sp++] = r; }
                }
            }
            nch++;
        }
    }
    if (nch == 0) return 0;
    for (int k = 0; k < g_nbox; k++) {
        int p = g_boxlist[k];
        if (b[p] != g_def && region_id[p] < 0) {
            if (nrg >= MAXRG) return 0;
            int sp = 0;
            bstack[sp++] = p;
            region_id[p] = nrg;
            while (sp) {
                int q = bstack[--sp];
                for (int d = 0; d < 4; d++) {
                    int r = q + D4[d];
                    if (g_inbox[r] && b[r] != g_def && region_id[r] < 0) { region_id[r] = nrg; bstack[sp++] = r; }
                }
            }
            nrg++;
        }
    }
    for (int r = 0; r < nrg; r++) {
        b_nempty[r] = 0;
        b_rok[r] = 1;
        memset(b_adj[r], 0, nch);
        memset(b_cnt[r], 0, nch * sizeof(int));
    }
    for (int k = 0; k < g_nbox; k++) {
        int p = g_boxlist[k];
        if (region_id[p] < 0) continue;
        int r = region_id[p];
        int seen[4], ns = 0;
        for (int d = 0; d < 4; d++) {
            int q = p + D4[d];
            if (!g_inbox[q]) {
                if (b[q] != EDGE) b_rok[r] = 0;
                continue;
            }
            if (b[q] == g_def) {
                int c = chain_id[q];
                b_adj[r][c] = 1;
                int dup = 0;
                for (int k2 = 0; k2 < ns; k2++) if (seen[k2] == c) dup = 1;
                if (!dup) seen[ns++] = c;
            }
        }
        if (b[p] == EMPTY) {
            b_nempty[r]++;
            for (int k2 = 0; k2 < ns; k2++) b_cnt[r][seen[k2]]++;
        }
    }
    memset(b_alive, 1, nch);
    int changed = 1;
    while (changed) {
        changed = 0;
        for (int r = 0; r < nrg; r++) {
            if (!b_rok[r]) continue;
            for (int c = 0; c < nch; c++)
                if (b_adj[r][c] && !b_alive[c]) { b_rok[r] = 0; break; }
        }
        for (int c = 0; c < nch; c++) {
            if (!b_alive[c]) continue;
            int v = 0;
            for (int r = 0; r < nrg; r++)
                if (b_rok[r] && b_adj[r][c] && b_nempty[r] > 0 && b_cnt[r][c] == b_nempty[r]) v++;
            if (v < 2) { b_alive[c] = 0; changed = 1; }
        }
    }
    int present = 0;
    for (int k = 0; k < g_ntarget; k++) {
        int p = g_targetlist[k];
        if (b[p] == g_def) {
            present = 1;
            if (!b_alive[chain_id[p]]) return 0;
        }
    }
    return present;
}

static int target_connected_to_safe(const uint8_t *b) {
    if (!g_def_has_safe) return 0;
    int stones[SZ], nl, sf;
    for (int k = 0; k < g_ntarget; k++) {
        int p = g_targetlist[k];
        if (b[p] == g_def) {
            get_chain(b, p, stones, &nl, &sf, NULL);
            if (sf) return 1;
        }
    }
    return 0;
}

static uint64_t state_key(const State *s, int tomove) {
    uint64_t k = s->hash ^ zob_settings;
    if (tomove == WHITE) k ^= zob_side;
    k ^= zob_ko[s->ko];
    if (s->lastpass) k ^= zob_pass;
    return k;
}

static void tt_lookup(uint64_t key, uint32_t *pn, uint32_t *dn) {
    TTE *e = &tt[key & (TTSIZE - 1)];
    if (e->key == key) { *pn = e->pn; *dn = e->dn; }
    else { *pn = 1; *dn = 1; }
}

static void tt_store(uint64_t key, uint32_t pn, uint32_t dn) {
    TTE *e = &tt[key & (TTSIZE - 1)];
    e->key = key; e->pn = pn; e->dn = dn;
}

typedef struct {
    State st;
    uint64_t key;
    int move;
    int term;   // 0 none, 1 attacker wins, 2 defender wins
    int score;
} Child;

static Child *childbuf[MAXD + 2];

#define TERM_A 1
#define TERM_D 2

static int lab[SZ], labgen[SZ], curgen = 1;
static int lablibs[SZ * 2], labsafe[SZ * 2], labtarget[SZ * 2];

static int gen_children(const State *s, int tomove, Child *ch) {
    // label chains for ordering
    curgen++;
    int stones[SZ], nl, sf, l1;
    int nlab = 0;
    for (int k = 0; k < g_nbox; k++) {
        int p = g_boxlist[k];
        if ((s->b[p] == BLACK || s->b[p] == WHITE) && labgen[p] != curgen) {
            int n = get_chain(s->b, p, stones, &nl, &sf, &l1);
            int ist = 0;
            for (int i = 0; i < n; i++) { lab[stones[i]] = nlab; labgen[stones[i]] = curgen; if (g_target[stones[i]]) ist = 1; }
            lablibs[nlab] = nl;
            labsafe[nlab] = sf;
            labtarget[nlab] = ist && s->b[p] == g_def;
            nlab++;
        }
    }
    int nc = 0;
    for (int i = 0; i < g_nregion; i++) {
        int p = g_regionlist[i];
        if (s->b[p] != EMPTY) continue;
        if (p == s->ko && tomove != g_kowin) continue;
        Child *c = &ch[nc];
        c->st = *s;
        int capt;
        if (!play(&c->st, p, tomove, &capt)) continue;
        c->move = p;
        c->term = 0;
        if (capt) c->term = TERM_A;
        else if (tomove == g_def && (target_connected_to_safe(c->st.b) || benson_targets_alive(c->st.b))) c->term = TERM_D;
        c->key = state_key(&c->st, 3 - tomove);
        int sc = 0;
        for (int d = 0; d < 4; d++) {
            int q = p + D4[d];
            int cc = s->b[q];
            if (cc == BLACK || cc == WHITE) {
                int L = lab[q];
                sc += 2;
                int libs = lablibs[L];
                if (cc != tomove) {
                    if (!labsafe[L]) {
                        if (libs == 1) sc += 50;
                        else if (libs == 2) sc += 12;
                        if (labtarget[L]) sc += 4;
                    }
                } else {
                    if (libs == 1) sc += 30;
                    else if (libs == 2) sc += 6;
                    if (labtarget[L]) sc += 3;
                }
            } else if (cc == EDGE) sc -= 1;
        }
        c->score = sc;
        nc++;
    }
    // sort by score desc
    for (int i = 1; i < nc; i++) {
        Child tmp = ch[i];
        int j = i - 1;
        while (j >= 0 && ch[j].score < tmp.score) { ch[j + 1] = ch[j]; j--; }
        ch[j + 1] = tmp;
    }
    // pass
    Child *c = &ch[nc];
    c->st = *s;
    c->move = PASSMOVE;
    c->score = -1000;
    if (s->lastpass) {
        c->term = g_strict ? (benson_targets_alive(s->b) ? TERM_D : TERM_A) : TERM_D;
        c->key = 0;
    } else {
        c->term = 0;
        c->st.lastpass = 1;
        c->st.ko = 0;
        c->key = state_key(&c->st, 3 - tomove);
    }
    nc++;
    return nc;
}

static inline uint32_t addcap(uint32_t a, uint32_t b) {
    uint64_t s = (uint64_t)a + b;
    return s >= INF ? INF : (uint32_t)s;
}

static void child_pd(Child *c, uint32_t *pn, uint32_t *dn) {
    if (c->term == TERM_A) { *pn = 0; *dn = INF; return; }
    if (c->term == TERM_D) { *pn = INF; *dn = 0; return; }
    for (int i = 0; i < pathlen; i++) {
        if (path[i] == c->key) {
            g_cyclehits++;
            if (g_strict) { *pn = 0; *dn = INF; } else { *pn = INF; *dn = 0; }
            return;
        }
    }
    tt_lookup(c->key, pn, dn);
}

static void mid(const State *s, int tomove, uint32_t thpn, uint32_t thdn, int depth, uint32_t *opn, uint32_t *odn) {
    g_nodes++;
    uint64_t key = state_key(s, tomove);
    if (g_maxnodes > 0 && g_nodes > g_maxnodes) g_aborted = 1;
    {
        TTE *e = &tt[key & (TTSIZE - 1)];
        if (e->key == key && (e->pn >= thpn || e->dn >= thdn || e->pn == 0 || e->dn == 0)) {
            *opn = e->pn; *odn = e->dn;
            return;
        }
    }
    if (depth >= MAXD) {
        g_depthhits++;
        *opn = INF; *odn = 0;
        tt_store(key, INF, 0);
        return;
    }
    Child *ch = childbuf[depth];
    int nc = gen_children(s, tomove, ch);
    path[pathlen++] = key;
    uint32_t pn = 1, dn = 1;
    int isor = (tomove == g_att);
    while (1) {
        uint32_t best1 = INF + 1, best2 = INF + 1;
        int bi = -1;
        uint32_t sum = 0, bpn = 0, bdn = 0;
        for (int i = 0; i < nc; i++) {
            uint32_t cp, cd;
            child_pd(&ch[i], &cp, &cd);
            uint32_t v = isor ? cp : cd;
            uint32_t o = isor ? cd : cp;
            sum = addcap(sum, o);
            if (v < best1) { best2 = best1; best1 = v; bi = i; bpn = cp; bdn = cd; }
            else if (v < best2) best2 = v;
        }
        if (isor) { pn = best1 > INF ? INF : best1; dn = sum; }
        else { dn = best1 > INF ? INF : best1; pn = sum; }
        if (pn >= thpn || dn >= thdn || pn == 0 || dn == 0 || g_aborted) break;
        uint32_t cthpn, cthdn;
        if (isor) {
            cthpn = thpn < (best2 >= INF ? INF : best2 + 1) ? thpn : (best2 >= INF ? INF : best2 + 1);
            // thdn - dn + bdn
            uint64_t t = (uint64_t)thdn + bdn;
            cthdn = t > dn ? (uint32_t)((t - dn) > INF ? INF : (t - dn)) : 0;
        } else {
            cthdn = thdn < (best2 >= INF ? INF : best2 + 1) ? thdn : (best2 >= INF ? INF : best2 + 1);
            uint64_t t = (uint64_t)thpn + bpn;
            cthpn = t > pn ? (uint32_t)((t - pn) > INF ? INF : (t - pn)) : 0;
        }
        uint32_t rp, rd;
        mid(&ch[bi].st, 3 - tomove, cthpn, cthdn, depth + 1, &rp, &rd);
    }
    pathlen--;
    tt_store(key, pn, dn);
    *opn = pn; *odn = dn;
}

// ---------------- API ----------------
static State g_root;

int setup(const char *boardstr, const char *regionstr, const char *safestr, const char *targetstr,
          int att, int kowin, int strict, int ko_point_idx, int lastpass) {
    init_zobrist();
    if (!childbuf[0])
        for (int d = 0; d < MAXD + 2; d++) childbuf[d] = (Child *)malloc(sizeof(Child) * MAXMV);
    memset(&g_root, 0, sizeof(g_root));
    memset(g_region, 0, sizeof(g_region));
    memset(g_safe, 0, sizeof(g_safe));
    memset(g_target, 0, sizeof(g_target));
    memset(g_inbox, 0, sizeof(g_inbox));
    for (int p = 0; p < SZ; p++) g_root.b[p] = EDGE;
    g_nregion = 0;
    g_ntarget = 0;
    g_def_has_safe = 0;
    int minx = 99, miny = 99, maxx = -1, maxy = -1;
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++) {
            int i = y * N + x;
            int p = (y + 1) * WD + (x + 1);
            char ch = boardstr[i];
            g_root.b[p] = ch == 'X' ? BLACK : ch == 'O' ? WHITE : EMPTY;
            if (g_root.b[p] != EMPTY) g_root.hash ^= zob[g_root.b[p]][p];
            if (regionstr[i] == '1') {
                g_region[p] = 1; g_regionlist[g_nregion++] = p;
                if (x < minx) minx = x; if (y < miny) miny = y; if (x > maxx) maxx = x; if (y > maxy) maxy = y;
            }
            if (safestr[i] == '1') g_safe[p] = 1;
            if (targetstr[i] == '1') {
                g_target[p] = 1; g_targetlist[g_ntarget++] = p;
                if (x < minx) minx = x; if (y < miny) miny = y; if (x > maxx) maxx = x; if (y > maxy) maxy = y;
            }
        }
    minx -= 2; miny -= 2; maxx += 2; maxy += 2;
    if (minx < 0) minx = 0; if (miny < 0) miny = 0; if (maxx > N - 1) maxx = N - 1; if (maxy > N - 1) maxy = N - 1;
    g_nbox = 0;
    for (int y = miny; y <= maxy; y++)
        for (int x = minx; x <= maxx; x++) {
            int p = (y + 1) * WD + (x + 1);
            g_inbox[p] = 1;
            g_boxlist[g_nbox++] = p;
        }
    g_att = att;
    g_def = 3 - att;
    g_kowin = kowin;
    g_strict = strict;
    for (int p = 0; p < SZ; p++)
        if (g_safe[p] && g_root.b[p] == g_def) g_def_has_safe = 1;
    if (ko_point_idx >= 0) {
        int y = ko_point_idx / N, x = ko_point_idx % N;
        g_root.ko = (y + 1) * WD + (x + 1);
    } else g_root.ko = 0;
    g_root.lastpass = lastpass;
    zob_settings = (uint64_t)att * 0x1234567ULL ^ (uint64_t)kowin * 0x89ABCDEF01ULL ^ (uint64_t)strict * 0x5555AAAA3333ULL;
    for (int p = 0; p < SZ; p++) {
        if (g_region[p]) zob_settings ^= zob[0][p] * 3;
        if (g_safe[p]) zob_settings ^= zob[0][p] * 5;
        if (g_target[p]) zob_settings ^= zob[0][p] * 7;
    }
    return g_nregion;
}

void clear_tt(void) {
    init_zobrist();
    memset(tt, 0, sizeof(TTE) * TTSIZE);
}

void set_limits(long long maxnodes, int maxdepth) {
    g_maxnodes = maxnodes;
    (void)maxdepth;
}

// returns 1 if attacker wins (proved), 0 if defender wins, -2 aborted
static uint64_t g_rootkey;
static int prove(const State *s, int tomove) {
    uint32_t pn, dn;
    path[0] = g_rootkey;
    pathlen = 1;
    mid(s, tomove, INF, INF, 0, &pn, &dn);
    if (g_aborted) return -2;
    if (pn == 0) return 1;
    if (dn == 0) return 0;
    return -2;
}

// results[i] for i in 0..360: -1 illegal/not in region, 0 loss, 1 win (for tomove); results[361] pass.
// Returns: 1 if tomove wins, 0 loses, -2 aborted, 3/2 already benson-alive (def wins / att loses).
int solve_all(int tomove, int *results, long long *stats, int allmoves) {
    g_nodes = 0;
    g_aborted = 0;
    g_depthhits = 0;
    g_cyclehits = 0;
    for (int i = 0; i < 362; i++) results[i] = -1;
    {
        int present = 0;
        for (int k = 0; k < g_ntarget; k++)
            if (g_root.b[g_targetlist[k]] == g_def) present = 1;
        if (!present) { stats[0] = 0; stats[1] = 0; return 4; }
    }
    if (benson_targets_alive(g_root.b)) {
        stats[0] = 0; stats[1] = 0;
        return tomove == g_def ? 3 : 2;
    }
    Child *ch = childbuf[MAXD + 1];
    int nc = gen_children(&g_root, tomove, ch);
    g_rootkey = state_key(&g_root, tomove);
    int any = 0;
    for (int k = 0; k < nc; k++) {
        Child *c = &ch[k];
        int w;
        if (c->term == TERM_A) w = (tomove == g_att);
        else if (c->term == TERM_D) w = (tomove == g_def);
        else {
            int r = prove(&c->st, 3 - tomove);
            if (r == -2) { stats[0] = g_nodes; stats[1] = g_depthhits; return -2; }
            w = (r == 1) == (tomove == g_att);
        }
        int idx;
        if (c->move == PASSMOVE) idx = 361;
        else { int y = c->move / WD - 1, x = c->move % WD - 1; idx = y * N + x; }
        results[idx] = w;
        if (w) { any = 1; if (!allmoves) break; }
    }
    stats[0] = g_nodes;
    stats[1] = g_depthhits * 1000000LL + g_cyclehits;
    return any;
}
