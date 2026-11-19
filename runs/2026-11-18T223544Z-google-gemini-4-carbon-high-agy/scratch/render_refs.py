#!/usr/bin/env python3
"""Render ASCII boards of the 20 reference problems with their main RIGHT line."""

import json
from pathlib import Path
from inspect_refs import parse_sgf

ROOT = Path(__file__).resolve().parent.parent


def sgf_to_rc(coord: str):
    return ord(coord[1]) - ord("a"), ord(coord[0]) - ord("a")


def find_right_lines(node, path=()):
    out = []
    mv = None
    for k in ("B", "W"):
        if k in node["props"]:
            mv = f"{k}[{node['props'][k][0]}]"
    cur = path + ((mv,) if mv else ())
    if any("RIGHT" in c for c in node["props"].get("C", [])):
        out.append(cur)
    for ch in node["children"]:
        out.extend(find_right_lines(ch, cur))
    return out


def render_board(ab, aw):
    pts = [sgf_to_rc(c) for c in ab | aw]
    r0 = max(0, min(r for r, _ in pts) - 1)
    r1 = min(18, max(r for r, _ in pts) + 1)
    c0 = max(0, min(c for _, c in pts) - 1)
    c1 = min(18, max(c for _, c in pts) + 1)
    bset = {sgf_to_rc(x) for x in ab}
    wset = {sgf_to_rc(x) for x in aw}
    cols = "abcdefghijklmnopqrs"
    lines = ["   " + " ".join(cols[c] for c in range(c0, c1 + 1))]
    for r in range(r0, r1 + 1):
        row_chars = []
        for c in range(c0, c1 + 1):
            if (r, c) in bset:
                row_chars.append("X")
            elif (r, c) in wset:
                row_chars.append("O")
            else:
                row_chars.append(".")
        lines.append(f"{cols[r]}  " + " ".join(row_chars))
    return "\n".join(lines)


def main():
    manifest = json.loads((ROOT / "inputs/reference-manifest.json").read_text())
    for p in manifest["problems"]:
        fname = Path(p["sgfFile"]).name
        root = parse_sgf((ROOT / "inputs/examples" / fname).read_text())
        ab = set(root["props"].get("AB", [])) - set(root["props"].get("AE", []))
        aw = set(root["props"].get("AW", [])) - set(root["props"].get("AE", []))
        rlines = find_right_lines(root)
        print(f"=== #{p['id']} ({p['rank']}, {p['playerColor']} to play) ===")
        print(render_board(ab, aw))
        for rl in rlines[:2]:
            print("  RIGHT:", " -> ".join(rl))
        print()


if __name__ == "__main__":
    main()
