import { canonicalInitialSetupFingerprint, parseSgf, type SgfNode } from "./sgf";

export interface BuiltInSetupDuplicate {
  id: string;
  label: string;
}

const COMMON_SETUP_DUPLICATES = [
  {
    id: "common-setup-001",
    label: "Common corner capture shape 001",
    sgf: "(;FF[4]GM[1]CA[UTF-8]SZ[19]AB[aq][bq][cq][dq][eq][er][es]AW[ar][br][cr][dr][ds])",
  },
  {
    id: "common-setup-002",
    label: "Common corner capture shape 002",
    sgf: "(;FF[4]GM[1]CA[UTF-8]SZ[19]AB[pa][pb][pc][pd][qd][qe][re][se]AW[qa][qb][qc][rc][rd][sd])",
  },
] as const;

const INDEXED_COMMON_SETUPS = COMMON_SETUP_DUPLICATES.map(({ id, label, sgf }) => ({
  id,
  label,
  fingerprint: canonicalInitialSetupFingerprint(parseSgf(sgf)),
}));

export function findBuiltInSetupDuplicate(root: SgfNode): BuiltInSetupDuplicate | null {
  const fingerprint = canonicalInitialSetupFingerprint(root);
  const match = INDEXED_COMMON_SETUPS.find((entry) => entry.fingerprint === fingerprint);
  return match ? { id: match.id, label: match.label } : null;
}
