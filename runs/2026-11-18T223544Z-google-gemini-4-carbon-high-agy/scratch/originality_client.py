#!/usr/bin/env python3
"""
Helper to check local reference/same-run originality first, then submit an originality
request to `originality/requests/<requestId>.json` and read `originality/results/<requestId>.json`.
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import canonical_setup_signatures, parse_sgf_strict, sgf_to_pt, validate_sgf_candidate

ROOT = Path(__file__).resolve().parent.parent


def load_board_masks(sgf_text: str):
    root, errs = parse_sgf_strict(sgf_text)
    if errs or root is None:
        raise ValueError(f"Parse errors: {errs}")
    b = 0
    w = 0
    for s in root.props.get("AB", []):
        b |= 1 << sgf_to_pt(s)
    for s in root.props.get("AW", []):
        w |= 1 << sgf_to_pt(s)
    for s in root.props.get("AE", []):
        p = sgf_to_pt(s)
        b &= ~(1 << p)
        w &= ~(1 << p)
    return b, w


def local_precheck(candidate_rel_path: str) -> list[str]:
    cand_path = ROOT / candidate_rel_path
    if not cand_path.exists():
        return [f"Missing file: {candidate_rel_path}"]
    raw = cand_path.read_text(encoding="utf-8")
    ok, errs, warns, info = validate_sgf_candidate(raw)
    if not ok:
        return [f"Validation error: {e}" for e in errs]

    b, w = load_board_masks(raw)
    c_d8, c_tr = canonical_setup_signatures(b, w)

    issues = []
    # Check against 20 reference SGFs
    for ref in sorted((ROOT / "inputs/examples").glob("*.sgf")):
        rb, rw = load_board_masks(ref.read_text(encoding="utf-8").replace("(\n;", "(;"))
        r_d8, r_tr = canonical_setup_signatures(rb, rw)
        if c_d8 == r_d8 or c_tr == r_tr:
            issues.append(f"Matches reference setup {ref.name}")

    # Check against other outputs/problem-*.sgf
    for out in sorted((ROOT / "outputs").glob("problem-*.sgf")):
        if out.resolve() == cand_path.resolve():
            continue
        ob, ow = load_board_masks(out.read_text(encoding="utf-8"))
        o_d8, o_tr = canonical_setup_signatures(ob, ow)
        if c_d8 == o_d8 or c_tr == o_tr:
            issues.append(f"Matches other output setup {out.name}")

    return issues


def query_originality(request_id: str, candidate_rel_path: str, timeout_s: float = 30.0) -> dict:
    issues = local_precheck(candidate_rel_path)
    if issues:
        raise RuntimeError(f"Aborted query {request_id} BEFORE spending budget due to local issues: {issues}")

    req_path = ROOT / "originality/requests" / f"{request_id}.json"
    res_path = ROOT / "originality/results" / f"{request_id}.json"
    if req_path.exists() or res_path.exists():
        raise RuntimeError(f"Request ID {request_id!r} already exists! Choose a fresh ID.")

    payload = {
        "requestId": request_id,
        "path": candidate_rel_path,
    }
    req_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if res_path.exists():
            try:
                txt = res_path.read_text(encoding="utf-8")
                if txt.strip():
                    return json.loads(txt)
            except json.JSONDecodeError:
                pass
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for {res_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 scratch/originality_client.py <requestId> <outputs/problem-XX.sgf>")
        sys.exit(2)
    rid, relp = sys.argv[1], sys.argv[2]
    res = query_originality(rid, relp)
    print(json.dumps(res, indent=2))
