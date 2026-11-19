#!/usr/bin/env python3
"""
Independent 7-dan referee audit of all 10 candidate SGFs in `outputs/` BEFORE final originality queries.
Checks:
1. Structural & SGF contract compliance on every file.
2. Minimum liberty count of EVERY non-captured outer wall chain across ALL nodes of the tree (detects any thin outer wall!).
3. Prints ASCII board + full SGF + authoring originality stats for human-eye inspection of all 10 problems.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import (
    BOARD_MASK, dilate, iter_components, opp_color, parse_sgf_strict,
    play_move, pt_to_sgf, sgf_to_pt, validate_sgf_candidate,
)

ROOT = Path(__file__).resolve().parent.parent


def render_ascii(b: int, w: int) -> str:
    pts = [divmod(p, 19) for p in range(361) if ((b | w) >> p) & 1]
    r0 = max(0, min(r for r, _ in pts) - 1)
    r1 = min(18, max(r for r, _ in pts) + 1)
    c0 = max(0, min(c for _, c in pts) - 1)
    c1 = min(18, max(c for _, c in pts) + 1)
    cols = "abcdefghijklmnopqrs"
    lines = ["   " + " ".join(cols[c] for c in range(c0, c1 + 1))]
    for r in range(r0, r1 + 1):
        row = []
        for c in range(c0, c1 + 1):
            bit = 1 << (r * 19 + c)
            if b & bit:
                row.append("X")
            elif w & bit:
                row.append("O")
            else:
                row.append(".")
        lines.append(f"{cols[r]}  " + " ".join(row))
    return "\n".join(lines)


def check_wall_liberties_along_tree(root, b0: int, w0: int):
    """Find initial chains with >=5 liberties (outer wall chains) and check their min liberties across the whole tree."""
    empty0 = BOARD_MASK ^ (b0 | w0)
    wall_seeds = []
    for col_name, mask in [("B", b0), ("W", w0)]:
        for ch in iter_components(mask):
            lc = (dilate(ch) & empty0).bit_count()
            if lc >= 5:
                wall_seeds.append((col_name, ch & -ch, lc))

    min_wall_lib = 999
    min_wall_desc = ""

    def walk(node, b, w, ko, path):
        nonlocal min_wall_lib, min_wall_desc
        empty = BOARD_MASK ^ (b | w)
        for col_name, seed_bit, init_lc in wall_seeds:
            cur_mask = b if col_name == "B" else w
            if not (cur_mask & seed_bit):
                min_wall_lib = 0
                min_wall_desc = f"{col_name} wall captured at {path}!"
                return
            for ch in iter_components(cur_mask):
                if ch & seed_bit:
                    lc = (dilate(ch) & empty).bit_count()
                    if lc < min_wall_lib:
                        min_wall_lib = lc
                        min_wall_desc = f"{col_name} wall ({init_lc}->min {lc} libs) at {path}"
        for child in node.children:
            mv_col = "B" if "B" in child.props else "W"
            mv_str = child.props[mv_col][0]
            nb, nw, nko = play_move(b, w, mv_col, sgf_to_pt(mv_str), ko)
            walk(child, nb, nw, nko, f"{path}->{mv_col}[{mv_str}]")

    walk(root, b0, w0, None, "root")
    return min_wall_lib, min_wall_desc


def main():
    out_files = sorted((ROOT / "outputs").iterdir())
    expected = [f"problem-{i:02d}.sgf" for i in range(1, 11)]
    actual = [f.name for f in out_files]
    assert actual == expected, f"Unexpected files in outputs/: {actual}"

    # Map latest authoring result by candidateSha256
    res_by_sha = {}
    for rf in sorted((ROOT / "originality/results").glob("*.json")):
        data = json.loads(rf.read_text())
        if data.get("candidateSha256"):
            res_by_sha[data["candidateSha256"]] = data

    b_first = 0
    w_first = 0
    for fname in expected:
        fpath = ROOT / "outputs" / fname
        raw = fpath.read_text(encoding="utf-8")
        sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        ok, errs, warns, info = validate_sgf_candidate(raw)
        assert ok and not errs and not warns, f"{fname}: {errs} {warns}"
        root, _ = parse_sgf_strict(raw)
        b = sum(1 << sgf_to_pt(s) for s in root.props["AB"])
        w = sum(1 << sgf_to_pt(s) for s in root.props["AW"])
        if info["first_player"] == "B":
            b_first += 1
        else:
            w_first += 1
        min_wl, wl_desc = check_wall_liberties_along_tree(root, b, w)
        ores = res_by_sha.get(sha, {})
        gp = ores.get("goProblems", {})
        loc = ores.get("local", {})
        print(f"============================================================")
        print(f"{fname} | 1st={info['first_player']} | stones={info['setup_stones']} | nodes={info['total_nodes']} | max_mv={info['max_moves']} | R={info['right_endpoints']} W={info['wrong_endpoints']}")
        print(f"  Wall min libs: {min_wl} ({wl_desc})")
        print(f"  Authoring check: status={ores.get('status')} topPct={gp.get('topPercentage')} sigs={len(gp.get('signatureMatches', []))} peerShape={loc.get('peerShapeMatches')}")
        print(render_ascii(b, w))
        print("  SGF:", raw.strip())
    print("============================================================")
    print(f"Summary: Black-first={b_first}, White-first={w_first}")


if __name__ == "__main__":
    main()
