#!/usr/bin/env python3
"""
Full-tree semantic verifier for tsumego SGF candidates using TsumegoSolver.
Verifies:
1. Structural validity & simplicity limits (<=14 moves, <=120 nodes, <=48 stones, SZ[19], no root comment).
2. Problem is non-trivial (if opponent moved first / protagonist did nothing, outcome would be worse).
3. Every optimal protagonist first move in combat_mask is included and leads to RIGHT.
4. Along every RIGHT branch:
   - Every protagonist move preserves the optimal outcome V*.
   - Any alternative optimal protagonist move at an internal protagonist node is ALSO covered as RIGHT!
   - Every antagonist move covered is answered optimally, AND we check whether any uncovered antagonist defense forces harder play or refutes!
5. Along every WRONG branch:
   - The mistaken protagonist move genuinely fails to achieve V* (`val != V*`).
   - Every antagonist refutation reply in the tree genuinely keeps protagonist below V*!
   - Wrong leaves end on antagonist's move.
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import (
    BOARD_MASK, SGFNode, TsumegoSolver, TsumegoSpec, opp_color,
    parse_sgf_strict, play_move, pt_to_sgf, sgf_to_pt, validate_sgf_candidate,
)


def subtree_has_right(node: SGFNode) -> bool:
    if any("RIGHT" in c for c in node.props.get("C", [])):
        return True
    return any(subtree_has_right(ch) for ch in node.children)


def verify_tree_against_solver(
    sgf_text: str,
    spec: TsumegoSpec,
    max_depth: int = 24,
) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    notes: List[str] = []

    ok, s_errs, s_warns, info = validate_sgf_candidate(sgf_text)
    errors.extend(s_errs)
    for w in s_warns:
        notes.append(f"WARN: {w}")
    if not ok:
        return False, errors, notes

    root, _ = parse_sgf_strict(sgf_text)
    assert root is not None

    solver = TsumegoSolver(spec, max_depth=max_depth)
    prot = spec.first_player
    ant = opp_color(prot)
    prot_is_def = (prot == spec.defender)

    def is_better_for_prot(a: int, b: int) -> bool:
        return a > b if prot_is_def else a < b

    # Check initial root value and opponent-first value (ensure problem isn't already settled!)
    root_moves = solver.analyze_moves(spec.black, spec.white, prot, None)
    if not root_moves:
        errors.append("No legal moves in combat_mask at root!")
        return False, errors, notes

    best_val = root_moves[0][1]
    notes.append(f"Root optimal value for {prot} ({'LIVE' if prot_is_def else 'KILL'}): {TsumegoSolver.OUTCOME_NAMES[best_val]} ({best_val})")

    opp_first_val = solver.evaluate(spec.black, spec.white, ant, None)
    notes.append(f"If {ant} played first instead: {TsumegoSolver.OUTCOME_NAMES[opp_first_val]} ({opp_first_val})")
    if opp_first_val == best_val:
        errors.append(f"Position is ALREADY settled ({TsumegoSolver.OUTCOME_NAMES[best_val]}) even if opponent plays first!")

    if prot_is_def and best_val == 0:
        errors.append("Defender to play, yet group is unconditionally DEAD on all moves!")
    if (not prot_is_def) and best_val == 4:
        errors.append("Attacker to play, yet group makes CLEAN_LIFE against all moves!")

    # Check all winning first moves at root
    winning_root_coords = {m for m, v in root_moves if v == best_val}
    sgf_root_right = set()
    sgf_root_wrong = set()
    for ch in root.children:
        mv = ch.props[prot][0]
        if subtree_has_right(ch):
            sgf_root_right.add(mv)
        else:
            sgf_root_wrong.add(mv)

    missing_root_wins = winning_root_coords - sgf_root_right
    if missing_root_wins:
        errors.append(f"Missing winning first move(s) at root: {sorted(missing_root_wins)} (marked wrong: {sorted(missing_root_wins & sgf_root_wrong)})")
    false_root_rights = sgf_root_right - winning_root_coords
    if false_root_rights:
        errors.append(f"First move(s) marked RIGHT do NOT achieve best value {best_val}: {sorted(false_root_rights)}")

    # Recursively audit every node in the SGF
    def audit_children(parent_children: List[SGFNode], b: int, w: int, ko: Optional[int], to_move: str, in_right_zone: bool, path_str: str):
        all_analyzed = dict(solver.analyze_moves(b, w, to_move, ko))
        if to_move == prot:
            win_moves = {m for m, v in all_analyzed.items() if v == best_val}
            right_kids = set()
            wrong_kids = set()
            for ch in parent_children:
                mv = ch.props[to_move][0]
                pt = sgf_to_pt(mv)
                res = play_move(b, w, to_move, pt, ko)
                assert res is not None
                nb, nw, nko = res
                val = solver.evaluate(nb, nw, opp_color(to_move), nko)
                has_r = subtree_has_right(ch)
                if has_r:
                    right_kids.add(mv)
                    if val != best_val:
                        errors.append(f"FALSE RIGHT at {path_str}->{to_move}[{mv}]: achieves {TsumegoSolver.OUTCOME_NAMES[val]} instead of {TsumegoSolver.OUTCOME_NAMES[best_val]}")
                else:
                    wrong_kids.add(mv)
                    if val == best_val:
                        errors.append(f"COOK IN WRONG BRANCH at {path_str}->{to_move}[{mv}]: achieves optimal {TsumegoSolver.OUTCOME_NAMES[val]} but lacks RIGHT!")
                    if not ch.children:
                        errors.append(f"Wrong branch stops on protagonist move without refutation at {path_str}->{to_move}[{mv}]")

                if ch.children:
                    audit_children(ch.children, nb, nw, nko, opp_color(to_move), has_r, f"{path_str}->{to_move}[{mv}]")

            if in_right_zone:
                omitted = win_moves - right_kids
                if omitted:
                    errors.append(f"Omitted equally-valid protagonist continuation(s) at {path_str}: {sorted(omitted)}")
        else:
            # Antagonist to move!
            for ch in parent_children:
                mv = ch.props[to_move][0]
                pt = sgf_to_pt(mv)
                res = play_move(b, w, to_move, pt, ko)
                assert res is not None
                nb, nw, nko = res
                val = solver.evaluate(nb, nw, opp_color(to_move), nko)
                has_r = subtree_has_right(ch)
                if in_right_zone:
                    if val != best_val:
                        errors.append(f"UNANSWERABLE DEFENSE at {path_str}->{to_move}[{mv}]: drops outcome to {TsumegoSolver.OUTCOME_NAMES[val]}!")
                    if not has_r:
                        errors.append(f"Antagonist defense {path_str}->{to_move}[{mv}] inside RIGHT tree has no RIGHT answer!")
                else:
                    # Inside a refutation branch: antagonist's move MUST actually refute!
                    if val == best_val:
                        errors.append(f"FAKE REFUTATION at {path_str}->{to_move}[{mv}]: protagonist can STILL achieve {TsumegoSolver.OUTCOME_NAMES[best_val]}!")
                if ch.children:
                    audit_children(ch.children, nb, nw, nko, opp_color(to_move), has_r, f"{path_str}->{to_move}[{mv}]")

            # Also report any strong uncovered antagonist defenses in RIGHT zone (where protagonist only has 1-2 winning replies!)
            if in_right_zone and parent_children:
                covered = {ch.props[to_move][0] for ch in parent_children}
                for m, v in all_analyzed.items():
                    if m in covered:
                        continue
                    pt = sgf_to_pt(m)
                    res = play_move(b, w, to_move, pt, ko)
                    if res is None:
                        continue
                    nb, nw, nko = res
                    # How many protagonist replies win against `m`?
                    replies = solver.analyze_moves(nb, nw, prot, nko)
                    wins = [rm for rm, rv in replies if rv == best_val]
                    if len(wins) <= 2:
                        notes.append(f"Uncovered tight defense at {path_str}: {to_move}[{m}] leaves only {len(wins)} winning reply/replies {wins}")

    audit_children(root.children, spec.black, spec.white, None, prot, True, "root")
    return len(errors) == 0, errors, notes
