// Exact local life-and-death solver: full reachable-state enumeration + attractor fixpoint.
// Semantics (history-free):
//   - attacker wins iff he can force capture of a target stone in finitely many moves
//   - two consecutive passes end the game (defender alive)
//   - ko regime: the designated ko-loser may never make a ko capture; the ko-winner may always
// Protocol identical to solver.cpp:
//   black/white/regboth/regatt/target/attacker/ready, then
//   q <A|D> <maxstates> <B|W tomove> [B|W xy]...
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>
#include <sstream>
#include <iostream>
#include <algorithm>
using namespace std;

static const int N = 19, W = 21, SZ = W * W;
static int8_t bd[SZ];
static bool reg[3][SZ];
static bool isTarget[SZ];
static vector<int> targets;
static int attacker = 1, defender = 2;
static int kowinner = 1;
static const int dirs[4] = {1, -1, W, -W};
static int stampArr[SZ];
static int stampCur = 0;
static vector<int> regpts;   // all playable points (either colour)
static vector<int> cells;    // variable cells = regpts minus target stones

static inline int P(int x, int y) { return (y + 1) * W + (x + 1); }
static string name(int p) {
    int x = p % W - 1, y = p / W - 1;
    string s;
    s += char('a' + x);
    s += char('a' + y);
    return s;
}
static int parsept(const string &s) { return P(s[0] - 'a', s[1] - 'a'); }

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
    int p, col;
    vector<int> caps;
};

static bool play(int p, int col, Undo &u, int &newko) {
    int opp = 3 - col;
    u.p = p;
    u.col = col;
    u.caps.clear();
    bd[p] = col;
    vector<int> grp;
    for (int d = 0; d < 4; d++) {
        int r = p + dirs[d];
        if (bd[r] == opp) {
            if (groupLibs(r, &grp) == 0) {
                for (int q : grp) {
                    bd[q] = 0;
                    u.caps.push_back(q);
                }
            }
        }
    }
    newko = 0;
    if (u.caps.empty()) {
        if (groupLibs(p, nullptr, 1) == 0) {
            bd[p] = 0;
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
    for (int q : u.caps) bd[q] = opp;
}
static bool targetCaptured() {
    for (int t : targets)
        if (bd[t] != defender) return true;
    return false;
}

// ---- state encoding ----
static inline uint64_t encode(int col, int passes) {
    uint64_t k = 0;
    for (int c : cells) k = k * 3 + (uint64_t)bd[c];
    return (k * 2 + (uint64_t)(col - 1)) * 2 + (uint64_t)passes;
}
static inline void decode(uint64_t k, int &col, int &passes) {
    passes = k & 1;
    k >>= 1;
    col = (int)(k & 1) + 1;
    k >>= 1;
    for (int i = (int)cells.size() - 1; i >= 0; i--) {
        bd[cells[i]] = (int8_t)(k % 3);
        k /= 3;
    }
}

static const int32_t T_WIN = -1, T_NOT = -2;
struct Table {
    unordered_map<uint64_t, int32_t> idx;
    vector<uint64_t> keys;
    vector<uint32_t> off;      // edge offsets (size n+1)
    vector<int32_t> edges;
    vector<uint8_t> win;       // 1 = attacker wins
    vector<uint8_t> fin;       // solved
};
static Table tabs[3];
static long long maxstates = 0;
static bool aborted = false;

// enumerate everything reachable from the current board (col to move, passes), then solve.
static int32_t ensure(int col, int passes) {
    Table &T = tabs[kowinner];
    uint64_t k0 = encode(col, passes);
    auto it0 = T.idx.find(k0);
    if (it0 != T.idx.end()) return it0->second;
    size_t first = T.keys.size();
    T.idx[k0] = (int32_t)first;
    T.keys.push_back(k0);
    T.win.push_back(0);
    T.fin.push_back(0);
    if (T.off.empty()) T.off.push_back(0);
    // BFS over new states; states are appended in order, edges generated in the same order
    for (size_t s = first; s < T.keys.size(); s++) {
        if (maxstates && (long long)(T.keys.size() - first) > maxstates) {
            aborted = true;
            break;
        }
        int c, ps;
        decode(T.keys[s], c, ps);
        int opp = 3 - c;
        bool isAtt = (c == attacker);
        for (int p : regpts) {
            if (bd[p] != 0 || !reg[c][p]) continue;
            Undo u;
            int nko;
            if (!play(p, c, u, nko)) continue;
            if (nko && c != kowinner) {
                undo(u);
                continue;
            }
            int32_t e;
            if (isAtt && !u.caps.empty() && targetCaptured()) {
                e = T_WIN;
            } else {
                uint64_t k = encode(opp, 0);
                auto it = T.idx.find(k);
                if (it == T.idx.end()) {
                    e = (int32_t)T.keys.size();
                    T.idx[k] = e;
                    T.keys.push_back(k);
                    T.win.push_back(0);
                    T.fin.push_back(0);
                } else
                    e = it->second;
            }
            undo(u);
            T.edges.push_back(e);
        }
        // pass
        if (ps == 1)
            T.edges.push_back(T_NOT);
        else {
            uint64_t k = encode(opp, 1);
            auto it = T.idx.find(k);
            int32_t e;
            if (it == T.idx.end()) {
                e = (int32_t)T.keys.size();
                T.idx[k] = e;
                T.keys.push_back(k);
                T.win.push_back(0);
                T.fin.push_back(0);
            } else
                e = it->second;
            T.edges.push_back(e);
        }
        T.off.push_back((uint32_t)T.edges.size());
    }
    if (aborted) {
        // roll back the partial enumeration
        for (size_t s = first; s < T.keys.size(); s++) T.idx.erase(T.keys[s]);
        T.keys.resize(first);
        T.win.resize(first);
        T.fin.resize(first);
        T.off.resize(first + 1);
        T.edges.resize(T.off[first]);
        return -3;
    }
    // least fixpoint: attacker wins iff capture can be forced in finite time
    size_t n = T.keys.size();
    bool changed = true;
    while (changed) {
        changed = false;
        for (size_t s = n; s-- > first;) {
            if (T.win[s]) continue;
            bool isAtt = ((int)((T.keys[s] >> 1) & 1) + 1) == attacker;
            bool w = !isAtt;
            for (uint32_t e = T.off[s]; e < T.off[s + 1]; e++) {
                int32_t t = T.edges[e];
                bool tw = (t == T_WIN) ? true : (t == T_NOT) ? false : (bool)T.win[t];
                if (isAtt && tw) {
                    w = true;
                    break;
                }
                if (!isAtt && !tw) {
                    w = false;
                    break;
                }
            }
            if (w) {
                T.win[s] = 1;
                changed = true;
            }
        }
    }
    for (size_t s = first; s < n; s++) T.fin[s] = 1;
    return (int32_t)first;
}

int main() {
    memset(bd, 3, sizeof(bd));
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++) bd[P(x, y)] = 0;
    string line;
    int8_t base[SZ];
    while (getline(cin, line)) {
        istringstream ss(line);
        string cmd;
        ss >> cmd;
        if (cmd == "black" || cmd == "white") {
            int c = cmd == "black" ? 1 : 2;
            string s;
            while (ss >> s) bd[parsept(s)] = c;
        } else if (cmd == "regboth") {
            string s;
            while (ss >> s) {
                int p = parsept(s);
                reg[1][p] = reg[2][p] = true;
            }
        } else if (cmd == "regatt") {
            string s;
            while (ss >> s) reg[attacker][parsept(s)] = true;
        } else if (cmd == "target") {
            string s;
            while (ss >> s) {
                int p = parsept(s);
                targets.push_back(p);
                isTarget[p] = true;
            }
        } else if (cmd == "attacker") {
            string s;
            ss >> s;
            attacker = s == "B" ? 1 : 2;
            defender = 3 - attacker;
        } else if (cmd == "ready") {
            memcpy(base, bd, sizeof(bd));
            for (int i = 0; i < SZ; i++)
                if (reg[1][i] || reg[2][i]) {
                    regpts.push_back(i);
                    if (!isTarget[i]) cells.push_back(i);
                }
            if (cells.size() > 38) {
                printf("TOOBIG\n");
                fflush(stdout);
                return 1;
            }
            printf("OK\n");
            fflush(stdout);
        } else if (cmd == "q") {
            string kw, tms;
            ss >> kw >> maxstates >> tms;
            int tomoveArg = tms == "B" ? 1 : 2;
            kowinner = (kw == "A") ? attacker : defender;
            memcpy(bd, base, sizeof(bd));
            int passes = 0;
            string cs, ms;
            bool err = false;
            int last = 0;
            while (ss >> cs >> ms) {
                int c = cs == "B" ? 1 : 2;
                last = c;
                if (ms == "pass") {
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
                passes = 0;
                if (targetCaptured()) {
                    printf("CAPTURED\n");
                    err = true;
                    break;
                }
            }
            if (!err) {
                int col = tomoveArg;
                if (passes == 1 && last == col) passes = 0;
                aborted = false;
                int8_t cur[SZ];
                memcpy(cur, bd, sizeof(bd));
                int32_t root = ensure(col, passes);
                memcpy(bd, cur, sizeof(bd));
                Table &T = tabs[kowinner];
                int opp = 3 - col;
                bool isAtt = col == attacker;
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
                    else if (root < 0)
                        rc = '?';
                    else {
                        auto it = T.idx.find(encode(opp, 0));
                        rc = (it == T.idx.end()) ? '?' : (T.win[it->second] ? '1' : '0');
                    }
                    undo(u);
                    printf("%s %c\n", name(p).c_str(), rc);
                }
                {
                    char rc;
                    if (passes == 1)
                        rc = '0';
                    else if (root < 0)
                        rc = '?';
                    else {
                        auto it = T.idx.find(encode(opp, 1));
                        rc = (it == T.idx.end()) ? '?' : (T.win[it->second] ? '1' : '0');
                    }
                    printf("pass %c\n", rc);
                }
            }
            printf("END\n");
            fflush(stdout);
        }
    }
    return 0;
}
