#!/usr/bin/env python3
"""
Submit one final originality query (`problem-01-final` .. `problem-10-final`)
for every exact final output file now that all 10 files exist in `outputs/`,
and verify that every single final file SHA-256 receives `status == 'clear'`
with zero peer or corpus matches.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from originality_client import query_originality
from go_engine import validate_sgf_candidate

ROOT = Path(__file__).resolve().parent.parent


def main():
    summary_rows = []
    for i in range(1, 11):
        rel_path = f"outputs/problem-{i:02d}.sgf"
        req_id = f"problem-{i:02d}-final"
        fpath = ROOT / rel_path
        raw = fpath.read_text(encoding="utf-8")
        ok, errs, warns, info = validate_sgf_candidate(raw)
        assert ok and not errs and not warns, f"Pre-final validation failed on {rel_path}: {errs} {warns}"

        sha_before = hashlib.sha256(fpath.read_bytes()).hexdigest()
        res = query_originality(req_id, rel_path, timeout_s=45.0)
        sha_after = hashlib.sha256(fpath.read_bytes()).hexdigest()

        assert sha_before == sha_after == res["candidateSha256"], f"SHA mismatch on {rel_path}!"
        status = res["status"]
        loc = res.get("local") or {}
        gp = res.get("goProblems") or {}
        summary_rows.append((
            rel_path,
            req_id,
            status,
            sha_after[:12],
            gp.get("topPercentage"),
            len(gp.get("signatureMatches") or []),
            len(loc.get("peerExactMatches") or []),
            len(loc.get("peerShapeMatches") or []),
            res.get("queriesRemaining"),
        ))
        print(
            f"{rel_path} [{req_id}]: status={status} sha={sha_after[:12]} "
            f"topPct={gp.get('topPercentage')} sigs={len(gp.get('signatureMatches') or [])} "
            f"peerExact={len(loc.get('peerExactMatches') or [])} peerShape={len(loc.get('peerShapeMatches') or [])} "
            f"rem={res.get('queriesRemaining')}"
        )
        assert status == "clear", f"NON-CLEAR FINAL STATUS on {rel_path}: {json.dumps(res, indent=2)}"
        assert not loc.get("peerExactMatches"), f"Peer exact match on {rel_path}: {loc}"
        assert not loc.get("peerShapeMatches"), f"Peer shape match on {rel_path}: {loc}"

    print("\nALL 10 FINAL CANDIDATES VERIFIED CLEAR WITH EXACT SHA256 MATCH!")


if __name__ == "__main__":
    main()
