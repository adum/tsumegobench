#!/usr/bin/env python3
"""Inspect all 20 reference SGFs to study their shapes, node counts, depths, and endpoints."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_sgf(text: str):
    text = text.strip()
    assert text.startswith("(") and text.endswith(")"), "Not parenthesized collection"
    idx = 0
    n = len(text)

    def skip_ws():
        nonlocal idx
        while idx < n and text[idx].isspace():
            idx += 1

    def parse_tree():
        nonlocal idx
        skip_ws()
        assert text[idx] == "(", f"Expected '(' at {idx}"
        idx += 1
        skip_ws()
        nodes = []
        while idx < n:
            skip_ws()
            if idx < n and text[idx] == ";":
                idx += 1
                props = {}
                while idx < n:
                    skip_ws()
                    if idx >= n or text[idx] in ";()":
                        break
                    m = re.match(r"[A-Za-z]+", text[idx:])
                    assert m, f"Expected prop ident at {idx}: {text[idx:idx+20]!r}"
                    ident = m.group(0)
                    idx += len(ident)
                    vals = []
                    skip_ws()
                    while idx < n and text[idx] == "[":
                        idx += 1
                        buf = []
                        while idx < n:
                            ch = text[idx]
                            idx += 1
                            if ch == "\\":
                                if idx < n:
                                    buf.append(text[idx])
                                    idx += 1
                            elif ch == "]":
                                break
                            else:
                                buf.append(ch)
                        vals.append("".join(buf))
                        skip_ws()
                    props.setdefault(ident, []).extend(vals)
                nodes.append({"props": props, "children": []})
            elif idx < n and text[idx] == "(":
                assert nodes, "Variation before any node"
                while idx < n:
                    skip_ws()
                    if idx < n and text[idx] == "(":
                        child = parse_tree()
                        nodes[-1]["children"].append(child)
                    else:
                        break
            elif idx < n and text[idx] == ")":
                idx += 1
                break
            else:
                raise ValueError(f"Unexpected char at {idx}: {text[idx]!r}")
        for i in range(len(nodes) - 1):
            nodes[i]["children"].insert(0, nodes[i + 1])
        return nodes[0]

    root = parse_tree()
    skip_ws()
    assert idx == n, f"Trailing content at {idx}: {text[idx:]!r}"
    return root


def stats(node, depth=0):
    total_nodes = 1
    max_depth = depth
    leaves = 0
    right_leaves = 0
    if not node["children"]:
        leaves = 1
        if any("RIGHT" in c for c in node["props"].get("C", [])):
            right_leaves = 1
    for ch in node["children"]:
        tn, md, lv, rl = stats(ch, depth + 1)
        total_nodes += tn
        max_depth = max(max_depth, md)
        leaves += lv
        right_leaves += rl
    return total_nodes, max_depth, leaves, right_leaves


def main():
    manifest = json.loads((ROOT / "inputs/reference-manifest.json").read_text())
    print(f"{'ID':>6} {'Rank':>7} {'Color':>5} {'AB+AW':>6} {'Nodes':>6} {'Depth':>5} {'1stBr':>5} {'Leaves':>6} {'Right':>5}")
    print("-" * 62)
    for p in manifest["problems"]:
        fname = Path(p["sgfFile"]).name
        sgf_text = (ROOT / "inputs/examples" / fname).read_text()
        root = parse_sgf(sgf_text)
        ab = set(root["props"].get("AB", [])) - set(root["props"].get("AE", []))
        aw = set(root["props"].get("AW", [])) - set(root["props"].get("AE", []))
        tn, md, lv, rl = stats(root, 0)
        first_br = len(root["children"])
        print(f"{p['id']:>6} {p['rank']:>7} {p['playerColor']:>5} {len(ab)+len(aw):>6} {tn:>6} {md:>5} {first_br:>5} {lv:>6} {rl:>5}")


if __name__ == "__main__":
    main()
