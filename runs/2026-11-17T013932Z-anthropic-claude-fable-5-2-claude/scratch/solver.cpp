// Local life-and-death solver (boolean alpha-beta with TT), persistent server.
// Protocol (stdin):
//   setup lines:
//     black <pts>          (sgf coords)
//     white <pts>
//     regboth <pts>        points both may play (when empty)
//     regatt <pts>         points only attacker may play
//     target <pts>         defender stones: attacker wins if any captured
//     attacker B|W
//     ready
//   queries:
//     q <A|D> <maxnodes> [B|W xy]...   -> replay moves, then list each legal move for side to move
//        output: "<xy|pass> <1|0|?>" per move  (1 = attacker wins after that move), then "END"
//        illegal replay -> "ERR ..." then "END"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <random>
using namespace std;

static const int N = 19, W = 21, SZ = W * W;
static int8_t bd[SZ];
static bool reg[3][SZ];
static vector<int> targets;
static int attacker = 1, defender = 2;
static uint64_t zob[3][SZ], zko[SZ + 1], zto[3], zpass[2];
static uint64_t h = 0;
static int kowinner = 1;
static unordered_map<uint64_t, uint8_t> tt[3];
static unordered_set<uint64_t> pathset;
static long long nodes = 0, maxnodes = 0;
static bool aborted = false;
static int hist[3][SZ];
static const int dirs[4] = {1, -1, W, -W};
static int stampArr[SZ];
static int stampCur = 0;
static vector<int> regpts;

static inline int P(int x, int y) { return (y + 1) * W + (x + 1); }
static string name(int p) {
    int x = p % W - 1, y = p / W - 1;
    string s;
    s += char('a' + x);
    s += char('a' + y);
    return s;
}
static int parsept(const string &s) { return P(s[0] - 'a', s[1] - 'a'); }

// count liberties (up to 2 needed) and collect group
static int groupLibs(int p, vector<int> *grp, int limit = 1000) {
    static int stack[SZ];
    int col = bd[p];
    ++stampCur;
    int sp = 0, libs = 0;
    stack[sp++] = p;
    stampArr[p] = stampCur;
    if (grp) grp->clear();
    while (sp) {
        int q = stack[--sp];
        if (grp) grp->push_back(q);
        for (int d = 0; d < 4; d++) {
            int r = q + dirs[d];
            if (stampArr[r] == stampCur) continue;
            if (bd[r] == 0) {
                stampArr[r] = stampCur;
                libs++;
                if (!grp && libs >= limit) return libs;
            } else if (bd[r] == col) {
                stampArr[r] = stampCur;
                stack[sp++] = r;
            }
        }
    }
    return libs;
}

struct Undo {
    int p;
    int col;
    vector<int> caps;
};

// returns false if illegal (suicide). sets newko (0 if none)
static bool play(int p, int col, Undo &u, int &newko) {
    int opp = 3 - col;
    u.p = p;
    u.col = col;
    u.caps.clear();
    bd[p] = col;
    h ^= zob[col][p];
    vector<int> grp;
    for (int d = 0; d < 4; d++) {
        int r = p + dirs[d];
        if (bd[r] == opp) {
            if (groupLibs(r, &grp) == 0) {
                for (int q : grp) {
                    bd[q] = 0;
                    h ^= zob[opp][q];
                    u.caps.push_back(q);
                }
            }
        }
    }
    newko = 0;
    if (u.caps.empty()) {
        if (groupLibs(p, nullptr, 1) == 0) {
            bd[p] = 0;
            h ^= zob[col][p];
            return false;
        }
    } else if (u.caps.size() == 1) {
        bool single = true;
        for (int d = 0; d < 4; d++)
            if (bd[p + dirs[d]] == col) single = false;
        if (single && groupLibs(p, nullptr, 2) == 1) newko = u.caps[0];
    }
    return true;
}
static void undo(const Undo &u) {
    int opp = 3 - u.col;
    bd[u.p] = 0;
    h ^= zob[u.col][u.p];
    for (int q : u.caps) {
        bd[q] = opp;
        h ^= zob[opp][q];
    }
}
static bool targetCaptured() {
    for (int t : targets)
        if (bd[t] != defender) return true;
    return false;
}

static inline uint64_t keyOf(int col, int ko, int passes) {
    return h ^ zto[col] ^ zko[ko] ^ zpass[passes];
}

static unordered_map<uint64_t, int> pathmap;
static const int INFD = 1000000;

// returns true if attacker wins. col to move. dep = shallowest ancestor depth the result depends on.
static bool search(int col, int ko, int passes, int depth, int &dep) {
    dep = INFD;
    if (aborted) return false;
    uint64_t key = keyOf(col, ko, passes);
    auto &T = tt[kowinner];
    static int nott = getenv("NOTT") ? 1 : 0;
    if (!nott) {
        auto it = T.find(key);
        if (it != T.end()) return it->second;
    }
    nodes++;
    if (maxnodes && nodes > maxnodes) {
        aborted = true;
        return false;
    }
    pathmap[key] = depth;
    bool isAtt = (col == attacker);
    bool result = !isAtt;
    int mv[64];
    int nm = 0;
    for (int p : regpts) {
        if (bd[p] != 0 || !reg[col][p]) continue;
        if (nm < 64) mv[nm++] = p;
    }
    sort(mv, mv + nm, [&](int a, int b) { return hist[col][a] > hist[col][b]; });
    bool done = false;
    int opp = 3 - col;
    int losedep = INFD, windep = INFD;
    for (int i = 0; i < nm && !done; i++) {
        int p = mv[i];
        Undo u;
        int nko;
        if (!play(p, col, u, nko)) continue;
        if (nko && col != kowinner) {
            undo(u);
            continue;  // ko loser never captures a ko
        }
        bool r;
        int cdep = INFD;
        if (isAtt && !u.caps.empty() && targetCaptured()) {
            r = true;
        } else {
            int cko = 0;
            uint64_t ck = keyOf(opp, cko, 0);
            auto pit = pathmap.find(ck);
            if (pit != pathmap.end()) {
                losedep = min(losedep, pit->second);
                undo(u);
                continue;  // repetition: illegal
            }
            r = search(opp, cko, 0, depth + 1, cdep);
        }
        undo(u);
        if (aborted) break;
        if ((isAtt && r) || (!isAtt && !r)) {
            result = isAtt;
            done = true;
            windep = cdep;
            hist[col][p] += 1;
        } else {
            losedep = min(losedep, cdep);
        }
    }
    if (!done && !aborted) {
        // pass
        if (passes == 1) {
            // two passes: defender alive
            if (!isAtt) { result = false; done = true; windep = INFD; }
            // attacker passing second: result false (alive) -> attacker fails via this option
        } else {
            uint64_t ck = keyOf(opp, 0, 1);
            auto pit = pathmap.find(ck);
            if (pit != pathmap.end()) {
                losedep = min(losedep, pit->second);
            } else {
                int cdep = INFD;
                bool r = search(opp, 0, 1, depth + 1, cdep);
                if (!aborted) {
                    if ((isAtt && r) || (!isAtt && !r)) {
                        result = isAtt;
                        done = true;
                        windep = cdep;
                    } else {
                        losedep = min(losedep, cdep);
                    }
                }
            }
        }
    }
    pathmap.erase(key);
    dep = done ? windep : losedep;
    if (!aborted) {
        if (dep >= depth) {
            if (!nott) T[key] = result;
            dep = INFD;
        }
    }
    return result;
}

int main() {
    memset(bd, 3, sizeof(bd));
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++) bd[P(x, y)] = 0;
    mt19937_64 rng(12345);
    for (int c = 0; c < 3; c++)
        for (int i = 0; i < SZ; i++) zob[c][i] = rng();
    for (int i = 0; i <= SZ; i++) zko[i] = rng();
    zko[0] = 0;
    for (int i = 0; i < 3; i++) zto[i] = rng();
    zpass[0] = 0;
    zpass[1] = rng();
    string line;
    int8_t base[SZ];
    uint64_t baseh = 0;
    while (getline(cin, line)) {
        istringstream ss(line);
        string cmd;
        ss >> cmd;
        if (cmd == "black" || cmd == "white") {
            int c = cmd == "black" ? 1 : 2;
            string s;
            while (ss >> s) {
                int p = parsept(s);
                bd[p] = c;
                h ^= zob[c][p];
            }
        } else if (cmd == "regboth") {
            string s;
            while (ss >> s) {
                int p = parsept(s);
                reg[1][p] = reg[2][p] = true;
            }
        } else if (cmd == "regatt") {
            string s;
            while (ss >> s) {
                int p = parsept(s);
                reg[attacker][p] = true;
            }
        } else if (cmd == "target") {
            string s;
            while (ss >> s) targets.push_back(parsept(s));
        } else if (cmd == "attacker") {
            string s;
            ss >> s;
            attacker = s == "B" ? 1 : 2;
            defender = 3 - attacker;
        } else if (cmd == "ready") {
            memcpy(base, bd, sizeof(bd));
            baseh = h;
            for (int i = 0; i < SZ; i++)
                if (reg[1][i] || reg[2][i]) regpts.push_back(i);
            if (getenv("TSEED")) {
                mt19937 g(atoi(getenv("TSEED")));
                shuffle(regpts.begin(), regpts.end(), g);
            }
            printf("OK\n");
            fflush(stdout);
        } else if (cmd == "q") {
            string kw;
            string tms;
            ss >> kw >> maxnodes >> tms;
            int tomoveArg = tms == "B" ? 1 : 2;
            kowinner = (kw == "A") ? attacker : defender;
            memcpy(bd, base, sizeof(bd));
            h = baseh;
            pathmap.clear();
            int col = 0, ko = 0, passes = 0;
            string cs, ms;
            bool err = false;
            int last = 0;
            int first = 0;
            while (ss >> cs >> ms) {
                int c = cs == "B" ? 1 : 2;
                if (!first) first = c;
                last = c;
                if (ms == "pass") {
                    ko = 0;
                    passes = 1;
                    continue;
                }
                int p = parsept(ms);
                if (bd[p] != 0) {
                    printf("ERR occupied %s\n", ms.c_str());
                    err = true;
                    break;
                }

                Undo u;
                int nko;
                if (!play(p, c, u, nko)) {
                    printf("ERR suicide %s\n", ms.c_str());
                    err = true;
                    break;
                }
                ko = 0;
                passes = 0;
                if (targetCaptured()) {
                    printf("CAPTURED\n");
                    err = true;
                    break;
                }
            }
            if (!err) {
                string tm;
                // side to move: opposite of last, or given by trailing token
                col = tomoveArg;
                if (passes == 1 && last == col) passes = 0;
                // optional override through env: none
                int opp = 3 - col;
                bool isAtt = col == attacker;
                nodes = 0;
                aborted = false;
                pathmap.clear();
                pathmap[keyOf(col, ko, passes)] = 0;
                for (int p : regpts) {
                    if (bd[p] != 0 || !reg[col][p]) continue;
                    Undo u;
                    int nko;
                    if (!play(p, col, u, nko)) continue;
                    if (nko && col != kowinner) {
                        undo(u);
                        printf("%s ko\n", name(p).c_str());
                        continue;
                    }
                    char rc;
                    if (isAtt && !u.caps.empty() && targetCaptured())
                        rc = '1';
                    else {
                        int cko = 0;
                        int dd; bool r = search(opp, cko, 0, 1, dd);
                        rc = aborted ? '?' : (r ? '1' : '0');
                    }
                    undo(u);
                    printf("%s %c\n", name(p).c_str(), rc);
                }
                {
                    bool r;
                    if (passes == 1)
                        r = false;
                    else
                        { int dd; r = search(opp, 0, 1, 1, dd); }
                    printf("pass %c\n", aborted ? '?' : (r ? '1' : '0'));
                }
            }
            printf("END\n");
            fflush(stdout);
        } else if (cmd == "first") {
            // set who moves first when no moves replayed: handled by client passing explicit colour
        }
    }
    return 0;
}
