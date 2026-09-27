// Local tsumego solver (boolean minimax with transposition table).
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
#define OUTSIDE 4   // pseudo-color for points outside local box (used in benson only)

static const int D4[4] = {1, -1, WD, -WD};

static uint8_t g_region[SZ], g_safe[SZ], g_target[SZ], g_inbox[SZ];
static int g_regionlist[SZ], g_nregion;
static int g_boxlist[SZ], g_nbox;
static int g_targetlist[SZ], g_ntarget;
static int g_att, g_def, g_kowin, g_strict;
static long long g_nodes, g_maxnodes;
static int g_maxdepth = 100;
static int g_aborted, g_depthhits, g_def_has_safe;

static uint64_t zob[3][SZ], zob_side, zob_ko[SZ], zob_pass, zob_settings;

typedef struct {
    uint8_t b[SZ];
    int ko;       // point banned for side to move (0 = none)
    int lastpass; // previous move was a pass that counts toward ending the game
    uint64_t hash;
} State;

typedef struct {
    uint64_t key;
    int8_t result;   // -1 none, 0/1 exact result
    int16_t best;    // hint move
} TTEntry;

#define TTBITS 23
#define TTSIZE (1u << TTBITS)
static TTEntry *tt = NULL;

static uint64_t path[4096];
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
    tt = (TTEntry *)calloc(TTSIZE, sizeof(TTEntry));
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

// Returns 1 if legal. Sets *cap_target if a target stone was captured.
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

// Benson unconditional life for all target chains of g_def, computed within local box.
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
    // region 0 reserved for "outside world": any region touching a non-box, non-edge point is merged conceptually
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
                if (b[q] != EDGE) b_rok[r] = 0; // touches outside world: never vital
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
    // chains touching outside world: treat as not alive (they are external groups we can't judge)
    for (int k = 0; k < g_nbox; k++) {
        int p = g_boxlist[k];
        if (b[p] != g_def) continue;
        for (int d = 0; d < 4; d++) {
            int q = p + D4[d];
            if (!g_inbox[q] && b[q] != EDGE) { /* chain extends beyond box */ }
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
    for (int k = 0; k < g_ntarget; k++) {
        int p = g_targetlist[k];
        if (b[p] == g_def && !b_alive[chain_id[p]]) return 0;
    }
    return 1;
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

// per-node chain labels for ordering
static int lab[SZ], labgen[SZ], curgen = 1;
static int lablibs[SZ * 2];
static int labsafe[SZ * 2];
static int labtarget[SZ * 2];

static int search(State *s, int tomove, int depth, int *taint);

static int search_child(State *s, int m, int tomove, int depth, int *legal, int *ctaint) {
    State c = *s;
    *ctaint = 0;
    *legal = 1;
    if (m == PASSMOVE) {
        if (s->lastpass) {
            int winner = g_strict ? (benson_targets_alive(s->b) ? g_def : g_att) : g_def;
            return winner == tomove;
        }
        c.lastpass = (s->ko == 0 || tomove == g_kowin) ? 1 : 0;
        c.ko = 0;
        int r = search(&c, 3 - tomove, depth + 1, ctaint);
        return !r;
    }
    int capt;
    if (!play(&c, m, tomove, &capt)) { *legal = 0; return 0; }
    if (capt) return tomove == g_att;
    if (tomove == g_def) {
        if (target_connected_to_safe(c.b)) return 1;
        if (benson_targets_alive(c.b)) return 1;
    }
    int r = search(&c, 3 - tomove, depth + 1, ctaint);
    return !r;
}

static int search(State *s, int tomove, int depth, int *taint) {
    *taint = 0;
    g_nodes++;
    if (g_maxnodes > 0 && g_nodes > g_maxnodes) { g_aborted = 1; *taint = 1; return 0; }
    if (g_aborted) { *taint = 1; return 0; }
    uint64_t key = state_key(s, tomove);
    for (int i = 0; i < pathlen; i++)
        if (path[i] == key) { *taint = 1; return tomove == g_kowin; }
    TTEntry *e = &tt[key & (TTSIZE - 1)];
    int hint = -1;
    if (e->key == key) {
        if (e->result >= 0) return e->result;
        hint = e->best;
    }
    if (depth >= g_maxdepth) { g_depthhits++; *taint = 1; return tomove == g_def; }

    // label chains in box
    curgen++;
    int stones[SZ], nl, sf, l1;
    int nlab = 0;
    int atk_quick = 0;
    for (int k = 0; k < g_nbox; k++) {
        int p = g_boxlist[k];
        if ((s->b[p] == BLACK || s->b[p] == WHITE) && labgen[p] != curgen) {
            int n = get_chain(s->b, p, stones, &nl, &sf, &l1);
            int ist = 0;
            for (int i = 0; i < n; i++) { lab[stones[i]] = nlab; labgen[stones[i]] = curgen; if (g_target[stones[i]]) ist = 1; }
            lablibs[nlab] = nl;
            labsafe[nlab] = sf;
            labtarget[nlab] = ist && s->b[p] == g_def;
            // quick win: attacker to move and target chain in atari with capturable liberty
            if (tomove == g_att && labtarget[nlab] && nl == 1 && !sf && g_region[l1] && (l1 != s->ko || g_kowin == g_att))
                atk_quick = 1;
            nlab++;
        }
    }
    if (atk_quick) return 1;

    int moves[SZ + 1], scores[SZ + 1], nm = 0;
    for (int i = 0; i < g_nregion; i++) {
        int p = g_regionlist[i];
        if (s->b[p] != EMPTY) continue;
        if (p == s->ko && tomove != g_kowin) continue;
        int sc = 0;
        for (int d = 0; d < 4; d++) {
            int q = p + D4[d];
            int c = s->b[q];
            if (c == BLACK || c == WHITE) {
                int L = lab[q];
                sc += 2;
                int libs = lablibs[L];
                if (c != tomove) {
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
            } else if (c == EDGE) {
                sc -= 1;
            }
        }
        if (p == hint) sc += 10000;
        moves[nm] = p;
        scores[nm] = sc;
        nm++;
    }
    for (int i = 1; i < nm; i++) {
        int m = moves[i], sc = scores[i], j = i - 1;
        while (j >= 0 && scores[j] < sc) { moves[j + 1] = moves[j]; scores[j + 1] = scores[j]; j--; }
        moves[j + 1] = m; scores[j + 1] = sc;
    }
    if (hint == PASSMOVE) {
        for (int i = nm; i > 0; i--) moves[i] = moves[i - 1];
        moves[0] = PASSMOVE;
        nm++;
    } else {
        moves[nm++] = PASSMOVE;
    }

    path[pathlen++] = key;
    int result = 0, anytaint = 0, best = -1;
    int tainted_win = 0, tainted_win_move = -1;
    for (int i = 0; i < nm; i++) {
        int legal, ct;
        int w = search_child(s, moves[i], tomove, depth, &legal, &ct);
        if (!legal) continue;
        if (g_aborted) break;
        if (w) {
            if (!ct) { result = 1; best = moves[i]; tainted_win = 0; break; }
            if (!tainted_win) { tainted_win = 1; tainted_win_move = moves[i]; }
        } else {
            if (ct) anytaint = 1;
        }
    }
    pathlen--;
    if (g_aborted) { *taint = 1; return 0; }
    if (!result && tainted_win) { result = 1; best = tainted_win_move; *taint = 1; }
    else if (!result) { *taint = anytaint; }
    if (!*taint) {
        e->key = key;
        e->result = (int8_t)result;
        e->best = (int16_t)best;
    } else {
        e->key = key;
        e->result = -1;
        e->best = (int16_t)best;
    }
    return result;
}

// ---------------- API ----------------
static State g_root;

int setup(const char *boardstr, const char *regionstr, const char *safestr, const char *targetstr,
          int att, int kowin, int strict, int ko_point_idx, int lastpass) {
    init_zobrist();
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
    // box = bounding box of region+targets expanded by 2
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
    memset(tt, 0, sizeof(TTEntry) * TTSIZE);
}

void set_limits(long long maxnodes, int maxdepth) {
    g_maxnodes = maxnodes;
    g_maxdepth = maxdepth;
}

// results[i] for i in 0..360: -1 illegal/not in region, 0 loss, 1 win (for tomove); results[361] pass.
// Returns: 1 if tomove wins, 0 loses, -2 aborted, 3/2 already benson-alive (def wins / att loses).
int solve_all(int tomove, int *results, long long *stats, int allmoves) {
    g_nodes = 0;
    g_aborted = 0;
    g_depthhits = 0;
    pathlen = 0;
    for (int i = 0; i < 362; i++) results[i] = -1;
    int any = 0;
    if (benson_targets_alive(g_root.b)) {
        stats[0] = 0; stats[1] = 0;
        return tomove == g_def ? 3 : 2;
    }
    path[pathlen++] = state_key(&g_root, tomove);
    for (int i = 0; i <= 361; i++) {
        int m;
        if (i == 361) m = PASSMOVE;
        else {
            int y = i / N, x = i % N;
            m = (y + 1) * WD + (x + 1);
            if (!g_region[m] || g_root.b[m] != EMPTY) continue;
        }
        int legal, ct;
        int w = search_child(&g_root, m, tomove, 0, &legal, &ct);
        if (!legal) continue;
        if (g_aborted) { stats[0] = g_nodes; stats[1] = g_depthhits; return -2; }
        results[i] = w;
        if (w) { any = 1; if (!allmoves) break; }
    }
    pathlen = 0;
    stats[0] = g_nodes;
    stats[1] = g_depthhits;
    return any;
}
