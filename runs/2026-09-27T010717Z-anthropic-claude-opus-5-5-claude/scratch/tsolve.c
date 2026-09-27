// Local life-and-death solver (iterative deepening alpha-beta with TT).
// Semantics: solver must reach goal unconditionally: opponent may retake ko
// immediately (unlimited threats), solver obeys simple ko; any repetition of
// (position, side) along the path counts as a solver loss.
// Defender wins if all key stones Benson-alive, or on two consecutive passes
// (unless strict). Attacker wins if any key stone captured.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define N 19
#define NN 361
#define EMPTY 0
#define BLACK 1
#define WHITE 2
#define WIN 1
#define LOSS 0
#define UNK 2

static int nei[NN][4], nnei[NN];
static uint64_t zob[NN][3];
static uint64_t zside[3], zpass, zko[NN + 1];

typedef struct { int8_t b[NN]; uint64_t h; } Board;

static int solver, goal_live, defender, attacker, strict, maxdepth;
static int keys[64], nkeys;
static int region[NN], nregion;
static long long nodes;

static uint64_t rng = 88172645463325252ULL;
static uint64_t xr(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; }

static void init(void) {
    for (int i = 0; i < NN; i++) {
        int x = i % N, y = i / N; nnei[i] = 0;
        if (x > 0) nei[i][nnei[i]++] = i - 1;
        if (x < N - 1) nei[i][nnei[i]++] = i + 1;
        if (y > 0) nei[i][nnei[i]++] = i - N;
        if (y < N - 1) nei[i][nnei[i]++] = i + N;
        for (int c = 0; c < 3; c++) zob[i][c] = xr();
    }
    for (int c = 0; c < 3; c++) zside[c] = xr();
    zpass = xr();
    for (int i = 0; i <= NN; i++) zko[i] = xr();
}

static inline void setp(Board *bd, int i, int c) {
    if (bd->b[i]) bd->h ^= zob[i][bd->b[i]];
    if (c) bd->h ^= zob[i][c];
    bd->b[i] = c;
}

// chain: fills stones, returns count; libs count (and optionally lib list)
static int mark[NN], markgen = 1;
static int chain(const Board *bd, int s, int *stones, int *nlibs, int *libs) {
    int c = bd->b[s]; int n = 0, nl = 0;
    markgen++;
    stones[n++] = s; mark[s] = markgen;
    static int lm[NN]; static int lgen = 1; lgen++;
    for (int k = 0; k < n; k++) {
        int p = stones[k];
        for (int j = 0; j < nnei[p]; j++) {
            int q = nei[p][j];
            if (bd->b[q] == c) { if (mark[q] != markgen) { mark[q] = markgen; stones[n++] = q; } }
            else if (bd->b[q] == EMPTY) { if (lm[q] != lgen) { lm[q] = lgen; if (libs) libs[nl] = q; nl++; } }
        }
    }
    *nlibs = nl; return n;
}

// returns number captured (>=0), or -1 if illegal. capone set to captured point if exactly one.
static int play(Board *bd, int i, int c, int *capone) {
    if (bd->b[i] != EMPTY) return -1;
    setp(bd, i, c);
    int o = 3 - c, ncap = 0, st[NN], nl;
    for (int j = 0; j < nnei[i]; j++) {
        int q = nei[i][j];
        if (bd->b[q] == o) {
            int n = chain(bd, q, st, &nl, NULL);
            if (nl == 0) { for (int k = 0; k < n; k++) setp(bd, st[k], EMPTY); if (ncap == 0 && n == 1) *capone = st[0]; ncap += n; }
        }
    }
    if (ncap == 0) {
        chain(bd, i, st, &nl, NULL);
        if (nl == 0) { setp(bd, i, EMPTY); return -1; }
    }
    return ncap;
}

// Benson: are all key stones pass-alive for defender?
static int benson_keys(const Board *bd) {
    int col = defender;
    static int cid[NN], rid[NN];
    static int cstart[NN], clen[NN], cst[NN];
    int nch = 0, pos = 0;
    for (int i = 0; i < NN; i++) cid[i] = -1, rid[i] = -1;
    for (int i = 0; i < NN; i++) if (bd->b[i] == col && cid[i] < 0) {
        int nl; int libs[NN];
        int n = chain(bd, i, cst + pos, &nl, libs);
        cstart[nch] = pos; clen[nch] = n;
        for (int k = 0; k < n; k++) cid[cst[pos + k]] = nch;
        pos += n; nch++;
    }
    // store libs as a char matrix instead (simpler)
    static unsigned char islib[NN][NN];
    for (int c = 0; c < nch; c++) {
        memset(islib[c], 0, NN);
    }
    for (int i = 0; i < NN; i++) if (bd->b[i] == EMPTY)
        for (int j = 0; j < nnei[i]; j++) { int q = nei[i][j]; if (bd->b[q] == col) islib[cid[q]][i] = 1; }
    // regions
    static int rpts[NN], rstart[NN], rlen[NN];
    int nr = 0; pos = 0;
    for (int i = 0; i < NN; i++) if (bd->b[i] != col && rid[i] < 0) {
        int s = pos; rpts[pos++] = i; rid[i] = nr;
        for (int k = s; k < pos; k++) {
            int p = rpts[k];
            for (int j = 0; j < nnei[p]; j++) { int q = nei[p][j]; if (bd->b[q] != col && rid[q] < 0) { rid[q] = nr; rpts[pos++] = q; } }
        }
        rstart[nr] = s; rlen[nr] = pos - s; nr++;
    }
    // adjacency lists per region
    static int radj[NN][16], nradj[NN], rbig[NN];
    static unsigned char vital[NN][16];
    for (int r = 0; r < nr; r++) {
        nradj[r] = 0; rbig[r] = 0;
        for (int k = 0; k < rlen[r]; k++) {
            int p = rpts[rstart[r] + k];
            for (int j = 0; j < nnei[p]; j++) {
                int q = nei[p][j];
                if (bd->b[q] == col) {
                    int c = cid[q], f = 0;
                    for (int m = 0; m < nradj[r]; m++) if (radj[r][m] == c) { f = 1; break; }
                    if (!f) { if (nradj[r] < 16) radj[r][nradj[r]++] = c; else rbig[r] = 1; }
                }
            }
        }
        for (int m = 0; m < nradj[r]; m++) {
            int c = radj[r][m], ok = 1;
            for (int k = 0; k < rlen[r] && ok; k++) {
                int p = rpts[rstart[r] + k];
                if (bd->b[p] == EMPTY && !islib[c][p]) ok = 0;
            }
            vital[r][m] = ok;
        }
    }
    static unsigned char calive[NN], ralive[NN];
    for (int c = 0; c < nch; c++) calive[c] = 1;
    for (int r = 0; r < nr; r++) ralive[r] = !rbig[r];
    for (;;) {
        int changed = 0;
        for (int c = 0; c < nch; c++) if (calive[c]) {
            int cnt = 0;
            for (int r = 0; r < nr && cnt < 2; r++) if (ralive[r])
                for (int m = 0; m < nradj[r]; m++) if (radj[r][m] == c && vital[r][m]) { cnt++; break; }
            if (cnt < 2) { calive[c] = 0; changed = 1; }
        }
        for (int r = 0; r < nr; r++) if (ralive[r]) {
            for (int m = 0; m < nradj[r]; m++) if (!calive[radj[r][m]]) { ralive[r] = 0; changed = 1; break; }
        }
        if (!changed) break;
    }
    for (int k = 0; k < nkeys; k++) {
        if (bd->b[keys[k]] != col) return 0;
        if (!calive[cid[keys[k]]]) return 0;
    }
    return 1;
}

#define BC_SIZE (1 << 20)
static uint64_t bc_key[BC_SIZE]; static int8_t bc_val[BC_SIZE];
static int key_alive(const Board *bd) {
    uint64_t h = bd->h | 1; int idx = (int)(h & (BC_SIZE - 1));
    if (bc_key[idx] == h) return bc_val[idx];
    int v = benson_keys(bd);
    bc_key[idx] = h; bc_val[idx] = v; return v;
}

static int key_captured(const Board *bd) {
    for (int k = 0; k < nkeys; k++) if (bd->b[keys[k]] != defender) return 1;
    return 0;
}

// TT
#define TT_SIZE (1 << 23)
typedef struct { uint64_t k; int8_t val; int8_t depthleft; int16_t best; } TTE;
static TTE *tt;

static uint64_t path[256]; static int plen;
static int in_path(uint64_t k) { for (int i = 0; i < plen; i++) if (path[i] == k) return 1; return 0; }

static int prune_eye = 1;

static int genmoves(const Board *bd, int color, int *mv) {
    int n = 0, st[NN], nl;
    for (int r = 0; r < nregion; r++) {
        int p = region[r];
        if (bd->b[p] != EMPTY) continue;
        if (prune_eye) {
            int own = 1;
            for (int j = 0; j < nnei[p]; j++) if (bd->b[nei[p][j]] != color) { own = 0; break; }
            if (own) {
                int ok = 1;
                for (int j = 0; j < nnei[p]; j++) { chain(bd, nei[p][j], st, &nl, NULL); if (nl < 2) { ok = 0; break; } }
                if (ok) continue;
            }
        }
        mv[n++] = p;
    }
    // ordering score
    int sc[NN];
    for (int k = 0; k < n; k++) {
        int p = mv[k], s = 0;
        for (int j = 0; j < nnei[p]; j++) {
            int q = nei[p][j];
            if (bd->b[q] != EMPTY) {
                chain(bd, q, st, &nl, NULL);
                if (nl <= 2) s += 4 * (3 - nl);
                s += 1;
                if (bd->b[q] == defender) s += 1;
            }
        }
        sc[k] = s;
    }
    for (int a = 1; a < n; a++) { int m = mv[a], s = sc[a], b = a - 1; while (b >= 0 && sc[b] < s) { mv[b + 1] = mv[b]; sc[b + 1] = sc[b]; b--; } mv[b + 1] = m; sc[b + 1] = s; }
    return n;
}

static inline uint64_t poskey(const Board *bd, int color) { return bd->h ^ zside[color]; }

// returns WIN/LOSS/UNK for solver; *dep set if path-dependent
static int search(const Board *bd, int color, int ko, int lastpass, int depthleft, int *dep) {
    nodes++;
    *dep = 0;
    if (key_captured(bd)) return goal_live ? LOSS : WIN;
    if (key_alive(bd)) return goal_live ? WIN : LOSS;
    if (depthleft <= 0) return UNK;
    uint64_t tk = bd->h ^ zside[color] ^ zko[ko < 0 ? NN : ko] ^ (lastpass ? zpass : 0);
    TTE *e = &tt[tk & (TT_SIZE - 1)];
    int ttbest = -2;
    if (e->k == tk) {
        if (e->val != UNK) return e->val;
        if (e->depthleft >= depthleft) return UNK;
        ttbest = e->best;
    }
    int solver_turn = (color == solver);
    int mv[NN + 1]; int n = genmoves(bd, color, mv);
    mv[n++] = -1; // pass
    if (ttbest >= -1) {
        for (int k = 0; k < n; k++) if (mv[k] == ttbest) { int t = mv[0]; mv[0] = mv[k]; mv[k] = t; break; }
    }
    int anyunk = 0, anydep = 0, result = -1, bestm = -2;
    for (int k = 0; k < n && result < 0; k++) {
        int m = mv[k], r, d = 0;
        if (m == -1) {
            if (lastpass) { r = strict ? (goal_live ? LOSS : WIN) : (goal_live ? WIN : LOSS); }
            else {
                uint64_t pk = poskey(bd, 3 - color) ^ zpass;
                if (in_path(pk)) { r = LOSS; d = 1; }
                else { path[plen++] = pk; r = search(bd, 3 - color, -1, 1, depthleft - 1, &d); plen--; }
            }
        } else {
            if (solver_turn && m == ko) continue;
            Board nb = *bd; int capone = -1;
            int nc = play(&nb, m, color, &capone);
            if (nc < 0) continue;
            int nko = -1;
            if (nc == 1) { int st[NN], nl; int ns = chain(&nb, m, st, &nl, NULL); if (ns == 1 && nl == 1) nko = capone; }
            uint64_t pk = poskey(&nb, 3 - color);
            if (in_path(pk)) { r = LOSS; d = 1; }
            else { path[plen++] = pk; r = search(&nb, 3 - color, nko, 0, depthleft - 1, &d); plen--; }
        }
        if (solver_turn) {
            if (r == WIN) { result = WIN; bestm = m; if (d) anydep = 1; else anydep = 0; }
            else { if (r == UNK) anyunk = 1; if (d) anydep = 1; }
        } else {
            if (r == LOSS) { result = LOSS; bestm = m; if (d) anydep = 1; else anydep = 0; }
            else { if (r == UNK) anyunk = 1; if (d) anydep = 1; }
        }
    }
    if (result < 0) result = anyunk ? UNK : (solver_turn ? LOSS : WIN);
    *dep = anydep;
    if (!anydep) {
        if (e->k != tk || result != UNK || e->val == UNK) {
            e->k = tk; e->val = result; e->depthleft = depthleft; e->best = bestm;
        }
    }
    return result;
}

static int lastlim;
static int solve_pos(const Board *bd, int color, int ko, int lastpass, int startpath) {
    int d, r = UNK;
    for (int lim = 1; lim <= maxdepth; lim += 1) {
        plen = startpath;
        r = search(bd, color, ko, lastpass, lim, &d);
        lastlim = lim;
        if (r != UNK) return r;
    }
    return UNK;
}

static const char *vs(int r) { return r == WIN ? "W" : r == LOSS ? "L" : "U"; }

int main(int argc, char **argv) {
    init();
    tt = calloc(TT_SIZE, sizeof(TTE));
    // input format:
    // solver goal strict maxdepth prune
    // nkeys k...
    // nregion r...
    // board (361 chars .XO)
    // tomove ko lastpass
    // cmd: value | all
    char gs[16], cmd[16];
    int sc, pr;
    if (scanf("%d %15s %d %d %d", &sc, gs, &strict, &maxdepth, &pr) != 5) return 1;
    prune_eye = pr;
    solver = sc; goal_live = (gs[0] == 'l');
    defender = goal_live ? solver : 3 - solver; attacker = 3 - defender;
    scanf("%d", &nkeys); for (int i = 0; i < nkeys; i++) scanf("%d", &keys[i]);
    scanf("%d", &nregion); for (int i = 0; i < nregion; i++) scanf("%d", &region[i]);
    char bs[NN + 8]; scanf("%s", bs);
    Board bd; memset(&bd, 0, sizeof bd);
    for (int i = 0; i < NN; i++) setp(&bd, i, bs[i] == 'X' ? BLACK : bs[i] == 'O' ? WHITE : EMPTY);
    int tomove, ko, lastpass; scanf("%d %d %d", &tomove, &ko, &lastpass);
    scanf("%15s", cmd);
    path[0] = poskey(&bd, tomove); plen = 1;
    if (strcmp(cmd, "value") == 0) {
        int r = solve_pos(&bd, tomove, ko, lastpass, 1);
        printf("value %s %d %lld\n", vs(r), lastlim, nodes);
        return 0;
    }
    // all: evaluate each move
    int mv[NN + 1]; int saved = prune_eye; prune_eye = 0;
    int n = genmoves(&bd, tomove, mv); prune_eye = saved;
    mv[n++] = -1;
    for (int k = 0; k < n; k++) {
        int m = mv[k], r; lastlim = 0;
        path[0] = poskey(&bd, tomove); plen = 1;
        if (m == -1) {
            if (lastpass) r = strict ? (goal_live ? LOSS : WIN) : (goal_live ? WIN : LOSS);
            else { path[1] = poskey(&bd, 3 - tomove) ^ zpass; r = solve_pos(&bd, 3 - tomove, -1, 1, 2); }
            printf("pass %s %d\n", vs(r), lastlim);
        } else {
            if (tomove == solver && m == ko) { printf("%d K\n", m); continue; }
            Board nb = bd; int capone = -1;
            int nc = play(&nb, m, tomove, &capone);
            if (nc < 0) { printf("%d I\n", m); continue; }
            int nko = -1;
            if (nc == 1) { int st[NN], nl; int ns = chain(&nb, m, st, &nl, NULL); if (ns == 1 && nl == 1) nko = capone; }
            int res; lastlim = 0;
            if (key_captured(&nb)) res = goal_live ? LOSS : WIN;
            else if (key_alive(&nb)) res = goal_live ? WIN : LOSS;
            else { path[1] = poskey(&nb, 3 - tomove); res = solve_pos(&nb, 3 - tomove, nko, 0, 2); }
            printf("%d %s %d\n", m, vs(res), lastlim);
        }
        fflush(stdout);
    }
    fprintf(stderr, "nodes %lld\n", nodes);
    return 0;
}
