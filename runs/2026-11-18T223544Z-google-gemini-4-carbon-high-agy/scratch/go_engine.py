#!/usr/bin/env python3
"""
Exact Go rules, Benson unconditional life, SGF validator, local symmetry canonicalizer,
and GHI-free Dual-Ko-Master Tsumego Solver on 19x19 bitboards.
"""

from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

BOARD_SIZE = 19
NUM_PTS = BOARD_SIZE * BOARD_SIZE
BOARD_MASK = (1 << NUM_PTS) - 1

NOT_COL_0 = 0
NOT_COL_18 = 0
for _r in range(BOARD_SIZE):
    for _c in range(BOARD_SIZE):
        _p = _r * BOARD_SIZE + _c
        if _c > 0:
            NOT_COL_0 |= 1 << _p
        if _c < BOARD_SIZE - 1:
            NOT_COL_18 |= 1 << _p

NEIGHBORS = [0] * NUM_PTS
for _p in range(NUM_PTS):
    _m = 1 << _p
    _nb = 0
    if _m & NOT_COL_0:
        _nb |= _m >> 1
    if _m & NOT_COL_18:
        _nb |= _m << 1
    if _p >= BOARD_SIZE:
        _nb |= _m >> BOARD_SIZE
    if _p < NUM_PTS - BOARD_SIZE:
        _nb |= _m << BOARD_SIZE
    NEIGHBORS[_p] = _nb


def dilate(mask: int) -> int:
    return (
        ((mask & NOT_COL_0) >> 1)
        | ((mask & NOT_COL_18) << 1)
        | (mask >> BOARD_SIZE)
        | ((mask << BOARD_SIZE) & BOARD_MASK)
    )


def flood_fill(seed: int, domain: int) -> int:
    comp = seed & domain
    if not comp:
        return 0
    while True:
        nxt = (comp | dilate(comp)) & domain
        if nxt == comp:
            return comp
        comp = nxt


def iter_bits(mask: int):
    while mask:
        lsb = mask & -mask
        yield lsb.bit_length() - 1
        mask ^= lsb


def iter_components(domain: int):
    rem = domain
    while rem:
        lsb = rem & -rem
        comp = flood_fill(lsb, rem)
        yield comp
        rem ^= comp


def sgf_to_pt(s: str) -> int:
    if len(s) != 2 or not ("a" <= s[0] <= "s" and "a" <= s[1] <= "s"):
        raise ValueError(f"Invalid 19x19 SGF coordinate: {s!r}")
    c = ord(s[0]) - 97
    r = ord(s[1]) - 97
    return r * BOARD_SIZE + c


def pt_to_sgf(p: int) -> str:
    r, c = divmod(p, BOARD_SIZE)
    return chr(97 + c) + chr(97 + r)


def opp_color(color: str) -> str:
    return "W" if color == "B" else "B"


def play_move(black: int, white: int, color: str, pt: int, ko_pt: Optional[int] = None) -> Optional[Tuple[int, int, Optional[int]]]:
    if pt < 0 or pt >= NUM_PTS or pt == ko_pt:
        return None
    bit = 1 << pt
    occ = black | white
    if occ & bit:
        return None

    own = black if color == "B" else white
    opp = white if color == "B" else black

    own_after = own | bit
    opp_adj = NEIGHBORS[pt] & opp
    captured = 0
    if opp_adj:
        empty_after_place = BOARD_MASK ^ (own_after | opp)
        checked = 0
        while opp_adj:
            lsb = opp_adj & -opp_adj
            opp_adj ^= lsb
            if lsb & checked:
                continue
            chain = flood_fill(lsb, opp)
            checked |= chain
            if (dilate(chain) & empty_after_place) == 0:
                captured |= chain

    opp_after = opp ^ captured
    empty_after = BOARD_MASK ^ (own_after | opp_after)

    if (NEIGHBORS[pt] & empty_after) and captured == 0:
        return (own_after, opp_after, None) if color == "B" else (opp_after, own_after, None)

    my_chain = flood_fill(bit, own_after)
    my_libs = dilate(my_chain) & empty_after
    if my_libs == 0:
        return None

    new_ko = None
    if captured and (captured & (captured - 1)) == 0 and my_chain == bit and (my_libs & (my_libs - 1)) == 0:
        new_ko = captured.bit_length() - 1

    return (own_after, opp_after, new_ko) if color == "B" else (opp_after, own_after, new_ko)


def benson_alive_mask(own: int, opp: int, immortal_own: int = 0, blocked_outside: int = 0) -> int:
    local_own = own & ~blocked_outside
    if not local_own:
        return own & immortal_own

    non_own = BOARD_MASK ^ own
    # Fast bound: enclose inside ~blocked_outside without flood-filling the entire 19x19 outside!
    # Wait: an intersection in ~blocked_outside leaks to blocked_outside iff it connects through non_own
    # to the 1-ring boundary of blocked_outside!
    inner_non_own = non_own & ~blocked_outside
    boundary_leak_seeds = dilate(blocked_outside & non_own) & inner_non_own
    leaked_inner = flood_fill(boundary_leak_seeds, inner_non_own) if boundary_leak_seeds else 0
    enclosed = inner_non_own ^ leaked_inner

    pure_empty_candidates = enclosed & ~opp
    if (pure_empty_candidates & (pure_empty_candidates - 1)) == 0 and not immortal_own:
        return 0

    chains: List[int] = list(iter_components(own))
    chain_idx_by_bit: Dict[int, int] = {}
    for idx, ch in enumerate(chains):
        m = ch
        while m:
            lsb = m & -m
            chain_idx_by_bit[lsb] = idx
            m ^= lsb

    immortal_set: Set[int] = {idx for idx, ch in enumerate(chains) if ch & immortal_own}

    regions: List[Tuple[int, Set[int], Set[int]]] = []
    for reg in iter_components(enclosed):
        if reg & opp:
            continue
        border_bits = dilate(reg) & own
        if not border_bits:
            continue
        border_chains: Set[int] = set()
        b = border_bits
        while b:
            lsb = b & -b
            border_chains.add(chain_idx_by_bit[lsb])
            b ^= lsb
        vital_for: Set[int] = set()
        for c_idx in border_chains:
            if (reg & ~dilate(chains[c_idx])) == 0:
                vital_for.add(c_idx)
        if vital_for:
            regions.append((reg, border_chains, vital_for))

    if len(regions) < 2 and not immortal_set:
        return 0

    alive_chains: Set[int] = set(range(len(chains)))
    alive_regions: Set[int] = set(range(len(regions)))

    changed = True
    while changed:
        changed = False
        dead_regs = [
            r_idx for r_idx in alive_regions
            if not regions[r_idx][1].issubset(alive_chains)
        ]
        if dead_regs:
            for r_idx in dead_regs:
                alive_regions.remove(r_idx)
            changed = True

        vital_counts = {c_idx: 0 for c_idx in alive_chains}
        for r_idx in alive_regions:
            for c_idx in regions[r_idx][2]:
                if c_idx in vital_counts:
                    vital_counts[c_idx] += 1

        dead_ch = [
            c_idx for c_idx in alive_chains
            if c_idx not in immortal_set and vital_counts[c_idx] < 2
        ]
        if dead_ch:
            for c_idx in dead_ch:
                alive_chains.remove(c_idx)
            changed = True

    res = 0
    for c_idx in alive_chains:
        res |= chains[c_idx]
    return res


@dataclass
class TsumegoSpec:
    black: int
    white: int
    first_player: str          # 'B' or 'W'
    defender: str              # 'B' or 'W'
    target_stones: int         # Core defender stones being attacked/defended
    combat_mask: int           # Playable / enclosed region mask
    outside_mask: int          # Open outside mask (cannot be a small eye for defender unless escaped)
    immortal_attacker: int     # Solid outer wall stones of attacker
    escape_mask: int = 0       # Optional points that signify defender escaped out


EMPTY_DEPS: FrozenSet = frozenset()
HORIZON_SENTINEL = ("HORIZON",)


class TsumegoSolver:
    OUTCOME_NAMES = {
        4: "CLEAN_LIFE",
        3: "KO_FOR_CLEAN_LIFE_OVER_SEKI",
        2: "SEKI",
        1: "KO",
        0: "DEAD",
    }

    def __init__(self, spec: TsumegoSpec, max_depth: int = 24):
        self.spec = spec
        self.attacker = opp_color(spec.defender)
        self.max_depth = max_depth
        self._tt_life: Dict[Tuple[int, int, Optional[int], str, Optional[str], int], bool] = {}
        self._tt_kill: Dict[Tuple[int, int, Optional[int], str, Optional[str], int], bool] = {}
        self.nodes_searched = 0
        self.combat_pts = list(iter_bits(spec.combat_mask))
        self.near_mask = spec.combat_mask | dilate(spec.combat_mask)

    def _ordered_moves(self, black: int, white: int, side: str, ko_pt: Optional[int]) -> List[int]:
        occ = black | white
        own = black if side == "B" else white
        opp = white if side == "B" else black
        empty = BOARD_MASK ^ occ

        urgent = 0
        semi_urgent = 0
        for ch in iter_components(opp & self.near_mask):
            libs = dilate(ch) & empty
            if libs and (libs & (libs - 1)) == 0:
                urgent |= libs
            elif libs.bit_count() == 2:
                semi_urgent |= libs
        for ch in iter_components(own & self.near_mask):
            libs = dilate(ch) & empty
            if libs and (libs & (libs - 1)) == 0:
                urgent |= libs
            elif libs.bit_count() == 2:
                semi_urgent |= libs

        hi = []
        mid = []
        lo = []
        orig_stones = self.spec.black | self.spec.white
        non_imm_stones = (black | white) & ~self.spec.immortal_attacker
        for pt in self.combat_pts:
            if pt == ko_pt:
                continue
            bit = 1 << pt
            if occ & bit:
                continue
            # Prune re-invading a captured corpse that touches neither any surviving non-immortal stone nor urgent liberty
            if (bit & orig_stones) and not (NEIGHBORS[pt] & non_imm_stones):
                continue
            if bit & urgent:
                hi.append(pt)
            elif (bit & semi_urgent) or (NEIGHBORS[pt] & occ):
                mid.append(pt)
            else:
                lo.append(pt)
        return hi + mid + lo

    def is_defender_clean_alive(self, black: int, white: int) -> bool:
        def_stones = black if self.spec.defender == "B" else white
        att_stones = white if self.spec.defender == "B" else black
        # Must preserve at least some stone connected to or inside combat_mask while target not wiped out?
        # Note: sacrificing 1 stone of target_stones is fine as long as a defender chain lives in the enclosure!
        zone = self.spec.target_stones | self.spec.combat_mask
        if (def_stones & zone) == 0:
            return False
        if self.spec.escape_mask and (def_stones & self.spec.escape_mask):
            for ch in iter_components(def_stones):
                if (ch & self.spec.escape_mask) and (dilate(ch) & ~(black | white)).bit_count() >= 4:
                    return True
        alive = benson_alive_mask(
            own=def_stones,
            opp=att_stones,
            immortal_own=0,
            blocked_outside=self.spec.outside_mask,
        )
        return (alive & zone) != 0

    def can_defender_make_clean_life(
        self,
        black: int,
        white: int,
        side: str,
        ko_pt: Optional[int],
        ko_master: Optional[str],
        depth: int = 0,
        pass_count: int = 0,
        path: FrozenSet = EMPTY_DEPS,
    ) -> Tuple[bool, FrozenSet]:
        self.nodes_searched += 1
        att_stones = white if self.spec.defender == "B" else black
        if (self.spec.immortal_attacker & ~att_stones) != 0:
            return True, EMPTY_DEPS

        def_stones = black if self.spec.defender == "B" else white
        if (def_stones & (self.spec.target_stones | self.spec.combat_mask)) == 0:
            return False, EMPTY_DEPS

        if self.is_defender_clean_alive(black, white):
            return True, EMPTY_DEPS

        if pass_count >= 2:
            return False, EMPTY_DEPS
        if depth >= self.max_depth:
            return False, frozenset({HORIZON_SENTINEL})

        state_key = (black, white, side, ko_pt is not None)
        if state_key in path:
            return False, frozenset({state_key})

        rem_d = self.max_depth - depth
        tt_key = (black, white, ko_pt, side, ko_master, pass_count)
        cached = self._tt_life.get(tt_key)
        if cached is not None:
            return cached, EMPTY_DEPS
        hcached = self._tt_life.get((tt_key, rem_d))
        if hcached is not None:
            return hcached, frozenset({HORIZON_SENTINEL})

        new_path = path | {state_key}
        is_def_turn = (side == self.spec.defender)
        opp = opp_color(side)
        moves = self._ordered_moves(black, white, side, ko_pt)

        if is_def_turn:
            acc_deps: Set = set()
            for pt in moves:
                res = play_move(black, white, side, pt, ko_pt)
                if res is None:
                    continue
                nb, nw, nko = res
                val, deps = self.can_defender_make_clean_life(nb, nw, opp, nko, ko_master, depth + 1, 0, new_path)
                if val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_life[tt_key] = True
                    return True, out_deps
                acc_deps.update(deps)
            if ko_pt is not None and ko_master == side:
                val, deps = self.can_defender_make_clean_life(black, white, side, None, ko_master, depth + 1, 0, new_path)
                if val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_life[tt_key] = True
                    return True, out_deps
                acc_deps.update(deps)

            acc_deps.discard(state_key)
            out_deps = frozenset(acc_deps)
            if not (out_deps - {HORIZON_SENTINEL}):
                if HORIZON_SENTINEL in out_deps:
                    self._tt_life[(tt_key, rem_d)] = False
                else:
                    self._tt_life[tt_key] = False
            return False, out_deps
        else:
            if pass_count >= 1:
                self._tt_life[tt_key] = False
                return False, EMPTY_DEPS
            acc_deps = set()
            for pt in moves:
                res = play_move(black, white, side, pt, ko_pt)
                if res is None:
                    continue
                nb, nw, nko = res
                val, deps = self.can_defender_make_clean_life(nb, nw, opp, nko, ko_master, depth + 1, 0, new_path)
                if not val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_life[tt_key] = False
                    return False, out_deps
                acc_deps.update(deps)
            if ko_pt is not None and ko_master == side:
                val, deps = self.can_defender_make_clean_life(black, white, side, None, ko_master, depth + 1, 0, new_path)
                if not val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_life[tt_key] = False
                    return False, out_deps
                acc_deps.update(deps)
            val, deps = self.can_defender_make_clean_life(black, white, opp, None, ko_master, depth + 1, pass_count + 1, new_path)
            if not val:
                out_deps = deps - {state_key}
                if not out_deps:
                    self._tt_life[tt_key] = False
                return False, out_deps
            acc_deps.update(deps)
            acc_deps.discard(state_key)
            out_deps = frozenset(acc_deps)
            if not (out_deps - {HORIZON_SENTINEL}):
                if HORIZON_SENTINEL in out_deps:
                    self._tt_life[(tt_key, rem_d)] = True
                else:
                    self._tt_life[tt_key] = True
            return True, out_deps

    def can_attacker_kill(
        self,
        black: int,
        white: int,
        side: str,
        ko_pt: Optional[int],
        ko_master: Optional[str],
        depth: int = 0,
        pass_count: int = 0,
        path: FrozenSet = EMPTY_DEPS,
    ) -> Tuple[bool, FrozenSet]:
        self.nodes_searched += 1
        att_stones = white if self.spec.defender == "B" else black
        if (self.spec.immortal_attacker & ~att_stones) != 0:
            return False, EMPTY_DEPS

        def_stones = black if self.spec.defender == "B" else white
        # Once all initial target stones AND all defender stones in combat_mask are captured, Defender is dead!
        if (def_stones & (self.spec.target_stones | self.spec.combat_mask)) == 0:
            return True, EMPTY_DEPS

        if self.is_defender_clean_alive(black, white):
            return False, EMPTY_DEPS

        if pass_count >= 2:
            return False, EMPTY_DEPS
        if depth >= self.max_depth:
            return False, frozenset({HORIZON_SENTINEL})

        state_key = (black, white, side, ko_pt is not None)
        if state_key in path:
            return False, frozenset({state_key})

        rem_d = self.max_depth - depth
        tt_key = (black, white, ko_pt, side, ko_master, pass_count)
        cached = self._tt_kill.get(tt_key)
        if cached is not None:
            return cached, EMPTY_DEPS
        hcached = self._tt_kill.get((tt_key, rem_d))
        if hcached is not None:
            return hcached, frozenset({HORIZON_SENTINEL})

        new_path = path | {state_key}
        is_att_turn = (side == self.attacker)
        opp = opp_color(side)
        moves = self._ordered_moves(black, white, side, ko_pt)

        if is_att_turn:
            acc_deps: Set = set()
            for pt in moves:
                res = play_move(black, white, side, pt, ko_pt)
                if res is None:
                    continue
                nb, nw, nko = res
                val, deps = self.can_attacker_kill(nb, nw, opp, nko, ko_master, depth + 1, 0, new_path)
                if val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_kill[tt_key] = True
                    return True, out_deps
                acc_deps.update(deps)
            if ko_pt is not None and ko_master == side:
                val, deps = self.can_attacker_kill(black, white, side, None, ko_master, depth + 1, 0, new_path)
                if val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_kill[tt_key] = True
                    return True, out_deps
                acc_deps.update(deps)

            acc_deps.discard(state_key)
            out_deps = frozenset(acc_deps)
            if not (out_deps - {HORIZON_SENTINEL}):
                if HORIZON_SENTINEL in out_deps:
                    self._tt_kill[(tt_key, rem_d)] = False
                else:
                    self._tt_kill[tt_key] = False
            return False, out_deps
        else:
            if pass_count >= 1:
                self._tt_kill[tt_key] = False
                return False, EMPTY_DEPS
            acc_deps = set()
            # Try PASS first when defender has >= 2 liberties on all chains (instant Seki cut!)
            empty = BOARD_MASK ^ (black | white)
            in_atari = False
            for ch in iter_components(def_stones & self.near_mask):
                libs = dilate(ch) & empty
                if libs and (libs & (libs - 1)) == 0:
                    in_atari = True
                    break
            if not in_atari:
                val, deps = self.can_attacker_kill(black, white, opp, None, ko_master, depth + 1, pass_count + 1, new_path)
                if not val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_kill[tt_key] = False
                    return False, out_deps
                acc_deps.update(deps)

            for pt in moves:
                res = play_move(black, white, side, pt, ko_pt)
                if res is None:
                    continue
                nb, nw, nko = res
                val, deps = self.can_attacker_kill(nb, nw, opp, nko, ko_master, depth + 1, 0, new_path)
                if not val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_kill[tt_key] = False
                    return False, out_deps
                acc_deps.update(deps)
            if ko_pt is not None and ko_master == side:
                val, deps = self.can_attacker_kill(black, white, side, None, ko_master, depth + 1, 0, new_path)
                if not val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_kill[tt_key] = False
                    return False, out_deps
                acc_deps.update(deps)
            if in_atari:
                val, deps = self.can_attacker_kill(black, white, opp, None, ko_master, depth + 1, pass_count + 1, new_path)
                if not val:
                    out_deps = deps - {state_key}
                    if not out_deps:
                        self._tt_kill[tt_key] = False
                    return False, out_deps
                acc_deps.update(deps)
            acc_deps.discard(state_key)
            out_deps = frozenset(acc_deps)
            if not (out_deps - {HORIZON_SENTINEL}):
                if HORIZON_SENTINEL in out_deps:
                    self._tt_kill[(tt_key, rem_d)] = True
                else:
                    self._tt_kill[tt_key] = True
            return True, out_deps

    def evaluate(self, black: int, white: int, side: str, ko_pt: Optional[int] = None) -> int:
        life_att_km, _ = self.can_defender_make_clean_life(black, white, side, ko_pt, self.attacker)
        if life_att_km:
            return 4
        kill_def_km, _ = self.can_attacker_kill(black, white, side, ko_pt, self.spec.defender)
        if kill_def_km:
            return 0

        life_def_km, _ = self.can_defender_make_clean_life(black, white, side, ko_pt, self.spec.defender)
        kill_att_km, _ = self.can_attacker_kill(black, white, side, ko_pt, self.attacker)

        if life_def_km and kill_att_km:
            return 1
        if life_def_km and not kill_att_km:
            return 3
        if not life_def_km and kill_att_km:
            return 1
        return 2

    def analyze_moves(self, black: int, white: int, side: str, ko_pt: Optional[int] = None) -> List[Tuple[str, int]]:
        results = []
        opp = opp_color(side)
        for pt in self._ordered_moves(black, white, side, ko_pt):
            res = play_move(black, white, side, pt, ko_pt)
            if res is None:
                continue
            nb, nw, nko = res
            val = self.evaluate(nb, nw, opp, nko)
            results.append((pt_to_sgf(pt), val))
        if side == self.spec.defender:
            results.sort(key=lambda x: (-x[1], x[0]))
        else:
            results.sort(key=lambda x: (x[1], x[0]))
        return results


# ---------------------------------------------------------------------------
# SGF Parser, Validator, and Canonical Fingerprint Checker
# ---------------------------------------------------------------------------

SUPPORTED_PROPS = {
    "B", "W", "AB", "AW", "AE", "C", "LB", "TR", "MA", "SZ",
    "FF", "GM", "CA", "AP",
}


@dataclass
class SGFNode:
    props: Dict[str, List[str]] = field(default_factory=dict)
    children: List["SGFNode"] = field(default_factory=list)


def parse_sgf_strict(raw: str) -> Tuple[Optional[SGFNode], List[str]]:
    errors: List[str] = []
    if "```" in raw:
        errors.append("Contains markdown code fence")
    s = raw.strip()
    if not (s.startswith("(;") and s.endswith(")")):
        errors.append("Must start with '(;' and end with ')' with no surrounding prose")
        return None, errors

    idx = 0
    n = len(s)

    def skip_ws():
        nonlocal idx
        while idx < n and s[idx].isspace():
            idx += 1

    def parse_collection() -> Optional[SGFNode]:
        nonlocal idx
        skip_ws()
        if idx >= n or s[idx] != "(":
            errors.append(f"Expected '(' at {idx}")
            return None
        idx += 1
        seq: List[SGFNode] = []
        while idx < n:
            skip_ws()
            if idx < n and s[idx] == ";":
                idx += 1
                props: Dict[str, List[str]] = {}
                while idx < n:
                    skip_ws()
                    if idx >= n or s[idx] in ";()":
                        break
                    m = re.match(r"[A-Za-z]+", s[idx:])
                    if not m:
                        errors.append(f"Expected property identifier at pos {idx}")
                        return None
                    ident = m.group(0)
                    idx += len(ident)
                    skip_ws()
                    if idx >= n or s[idx] != "[":
                        errors.append(f"Property {ident} without value at pos {idx}")
                        return None
                    vals: List[str] = []
                    while idx < n and s[idx] == "[":
                        idx += 1
                        buf: List[str] = []
                        closed = False
                        while idx < n:
                            ch = s[idx]
                            idx += 1
                            if ch == "\\":
                                if idx < n:
                                    buf.append(s[idx])
                                    idx += 1
                            elif ch == "]":
                                closed = True
                                break
                            else:
                                buf.append(ch)
                        if not closed:
                            errors.append(f"Unclosed '[' in property {ident}")
                            return None
                        vals.append("".join(buf))
                        skip_ws()
                    props.setdefault(ident, []).extend(vals)
                seq.append(SGFNode(props=props))
            elif idx < n and s[idx] == "(":
                if not seq:
                    errors.append("Sub-variation before any node")
                    return None
                while idx < n:
                    skip_ws()
                    if idx < n and s[idx] == "(":
                        sub = parse_collection()
                        if sub is None:
                            return None
                        seq[-1].children.append(sub)
                    else:
                        break
            elif idx < n and s[idx] == ")":
                idx += 1
                break
            else:
                errors.append(f"Unexpected character {s[idx]!r} at pos {idx}")
                return None
        if not seq:
            errors.append("Empty SGF variation")
            return None
        for i in range(len(seq) - 1):
            seq[i].children.insert(0, seq[i + 1])
        return seq[0]

    root = parse_collection()
    skip_ws()
    if idx != n:
        errors.append(f"Extra content after closing ')' at pos {idx} (multiple collections or trailing prose)")
    return root, errors


def validate_sgf_candidate(raw: str) -> Tuple[bool, List[str], List[str], Dict]:
    root, errors = parse_sgf_strict(raw)
    warnings: List[str] = []
    info: Dict = {}
    if root is None or errors:
        return False, errors, warnings, info

    rp = root.props
    if rp.get("SZ") != ["19"]:
        errors.append(f"Root must declare explicit SZ[19], got {rp.get('SZ')}")
    if "B" in rp or "W" in rp:
        errors.append("Root must not contain B or W move")
    if "C" in rp:
        errors.append("Root must not contain C[...] comment")
    if "AB" not in rp or "AW" not in rp or not rp["AB"] or not rp["AW"]:
        errors.append("Root must contain both AB and AW setup stones")

    for k in rp:
        if k not in SUPPORTED_PROPS:
            warnings.append(f"Unsupported root property: {k}")

    black = 0
    white = 0
    for c_str in rp.get("AB", []):
        try:
            p = sgf_to_pt(c_str)
            if (black | white) & (1 << p):
                errors.append(f"Duplicate setup stone at {c_str}")
            black |= 1 << p
        except ValueError as e:
            errors.append(str(e))
    for c_str in rp.get("AW", []):
        try:
            p = sgf_to_pt(c_str)
            if (black | white) & (1 << p):
                errors.append(f"Overlapping setup stone at {c_str}")
            white |= 1 << p
        except ValueError as e:
            errors.append(str(e))
    for c_str in rp.get("AE", []):
        p = sgf_to_pt(c_str)
        black &= ~(1 << p)
        white &= ~(1 << p)

    setup_count = (black | white).bit_count()
    info["setup_stones"] = setup_count
    if setup_count > 48:
        warnings.append(f"Setup stones ({setup_count}) exceeds preferred limit of 48")

    empty0 = BOARD_MASK ^ (black | white)
    for ch in iter_components(black):
        if (dilate(ch) & empty0) == 0:
            errors.append("Initial Black setup chain has 0 liberties")
    for ch in iter_components(white):
        if (dilate(ch) & empty0) == 0:
            errors.append("Initial White setup chain has 0 liberties")

    if not root.children:
        errors.append("Root has no solution branches")
        return False, errors, warnings, info

    first_colors: Set[str] = set()
    total_nodes = 1
    max_line_moves = 0
    right_endpoints = 0
    wrong_endpoints = 0

    def walk(node: SGFNode, b: int, w: int, ko: Optional[int], expected_color: Optional[str], depth: int, path_str: str):
        nonlocal total_nodes, max_line_moves, right_endpoints, wrong_endpoints
        total_nodes += 1
        max_line_moves = max(max_line_moves, depth)
        np = node.props
        for k in np:
            if k not in SUPPORTED_PROPS:
                warnings.append(f"Unsupported node property {k} at {path_str}")
            if k in ("AB", "AW", "AE"):
                errors.append(f"Setup property {k} used after root at {path_str}")

        has_b = "B" in np
        has_w = "W" in np
        if has_b == has_w:
            errors.append(f"Node at {path_str} must have exactly one B or W move")
            return
        col = "B" if has_b else "W"
        vals = np[col]
        if len(vals) != 1:
            errors.append(f"Node at {path_str} has multiple moves in {col}: {vals}")
            return
        mv_str = vals[0]
        if depth == 1:
            first_colors.add(col)
        elif col != expected_color:
            errors.append(f"Non-alternating move color at {path_str}: expected {expected_color}, got {col}")

        if mv_str == "" or mv_str == "tt":
            errors.append(f"Pass move not allowed at {path_str}")
            return
        try:
            pt = sgf_to_pt(mv_str)
        except ValueError as e:
            errors.append(f"{e} at {path_str}")
            return

        res = play_move(b, w, col, pt, ko)
        if res is None:
            errors.append(f"Illegal Go move {col}[{mv_str}] at {path_str} (occupied, ko, or suicide)")
            return
        nb, nw, nko = res

        comments = np.get("C", [])
        c_joined = "\n".join(comments)
        if "<" in c_joined or ">" in c_joined or "javascript:" in c_joined.lower():
            errors.append(f"HTML/JS suspect in comment at {path_str}: {c_joined!r}")
        has_right = "RIGHT" in c_joined
        if has_right and node.children:
            errors.append(f"RIGHT marker on non-leaf node at {path_str}")

        if not node.children:
            if has_right:
                right_endpoints += 1
            else:
                wrong_endpoints += 1
                if first_colors and col in first_colors:
                    warnings.append(f"Wrong leaf ends on protagonist's move at {path_str} -> {col}[{mv_str}]")
        else:
            seen_child_moves: Set[Tuple[str, str]] = set()
            for ch in node.children:
                ccol = "B" if "B" in ch.props else ("W" if "W" in ch.props else "?")
                cmv = ch.props.get(ccol, ["?"])[0]
                if (ccol, cmv) in seen_child_moves:
                    errors.append(f"Duplicate sibling branch {ccol}[{cmv}] under {path_str} -> {col}[{mv_str}]")
                seen_child_moves.add((ccol, cmv))
                walk(ch, nb, nw, nko, opp_color(col), depth + 1, f"{path_str}->{col}[{mv_str}]")

    seen_root_moves: Set[Tuple[str, str]] = set()
    for ch in root.children:
        ccol = "B" if "B" in ch.props else ("W" if "W" in ch.props else "?")
        cmv = ch.props.get(ccol, ["?"])[0]
        if (ccol, cmv) in seen_root_moves:
            errors.append(f"Duplicate first-move branch {ccol}[{cmv}]")
        seen_root_moves.add((ccol, cmv))
        walk(ch, black, white, None, None, 1, "root")

    if len(first_colors) > 1:
        errors.append(f"Inconsistent first-move colors: {first_colors}")
    first_player = next(iter(first_colors)) if first_colors else "?"
    info["first_player"] = first_player
    info["total_nodes"] = total_nodes
    info["max_moves"] = max_line_moves
    info["right_endpoints"] = right_endpoints
    info["wrong_endpoints"] = wrong_endpoints

    if max_line_moves > 14:
        errors.append(f"Longest line ({max_line_moves} moves) exceeds hard limit of 14")
    if total_nodes > 120:
        errors.append(f"Total nodes ({total_nodes}) exceeds hard limit of 120")
    if right_endpoints == 0:
        errors.append("No accepted solution endpoint marked with C[RIGHT]")

    return len(errors) == 0, errors, warnings, info


# ---------------------------------------------------------------------------
# Symmetries & Local Canonical Setup Fingerprints
# ---------------------------------------------------------------------------

def d8_transforms(r: int, c: int, mode: int) -> Tuple[int, int]:
    N = BOARD_SIZE - 1
    if mode == 0:
        return r, c
    elif mode == 1:
        return c, N - r
    elif mode == 2:
        return N - r, N - c
    elif mode == 3:
        return N - c, r
    elif mode == 4:
        return r, N - c
    elif mode == 5:
        return N - r, c
    elif mode == 6:
        return c, r
    elif mode == 7:
        return N - c, N - r
    raise ValueError(mode)


def canonical_setup_signatures(black: int, white: int) -> Tuple[str, str]:
    pts_b = [divmod(p, BOARD_SIZE) for p in iter_bits(black)]
    pts_w = [divmod(p, BOARD_SIZE) for p in iter_bits(white)]

    d8_forms = []
    trans_forms = []
    for swap in (False, True):
        sb, sw = (pts_w, pts_b) if swap else (pts_b, pts_w)
        for mode in range(8):
            tb = sorted(d8_transforms(r, c, mode) for r, c in sb)
            tw = sorted(d8_transforms(r, c, mode) for r, c in sw)
            d8_forms.append((tb, tw))
            all_pts = tb + tw
            if all_pts:
                min_r = min(r for r, _ in all_pts)
                min_c = min(c for _, c in all_pts)
                nb = [(r - min_r, c - min_c) for r, c in tb]
                nw = [(r - min_r, c - min_c) for r, c in tw]
                trans_forms.append((nb, nw))
    best_d8 = repr(min(d8_forms))
    best_tr = repr(min(trans_forms))
    return (
        hashlib.sha256(best_d8.encode()).hexdigest()[:16],
        hashlib.sha256(best_tr.encode()).hexdigest()[:16],
    )
