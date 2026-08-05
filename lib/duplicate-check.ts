import { readFile } from "node:fs/promises";
import path from "node:path";
import { findSimilarProblems, type SimilarProblem } from "./goproblems";
import {
  canonicalProblemFingerprint,
  canonicalRightShapes,
  parseSgf,
  shapeSimilarity,
  type SgfNode,
} from "./sgf";

export interface DuplicateReferenceRecord {
  id: number;
  rank?: string;
  sgfFile: string;
  sourceUrl: string;
}

interface DuplicateManifest {
  problems: DuplicateReferenceRecord[];
}

interface IndexedReference {
  record: DuplicateReferenceRecord;
  fingerprint: string;
  rightShapes: string[];
}

export interface DuplicateCorpus {
  references: IndexedReference[];
}

export interface DuplicateMatch {
  id: number;
  sourceUrl: string;
}

export interface LocalShapeMatch extends DuplicateMatch {
  percentage: number;
}

export interface RemoteDuplicateReport {
  status: "pass" | "fail" | "manual_review" | "not_run" | "error";
  radiusTwoMatches: Array<Pick<SimilarProblem, "id" | "difficulty" | "createdAt">>;
  topPercentage: number | null;
  topMatchId: number | null;
  error: string | null;
}

export interface DuplicateReport {
  status: "pass" | "fail" | "manual_review" | "not_run";
  exactLocalMatch: DuplicateMatch | null;
  closestLocalShape: LocalShapeMatch | null;
  remote: RemoteDuplicateReport;
}

export async function loadDuplicateCorpus(projectRoot = process.cwd()): Promise<DuplicateCorpus> {
  const manifest = JSON.parse(
    await readFile(path.join(projectRoot, "examples", "manifest.json"), "utf8"),
  ) as DuplicateManifest;

  const references: IndexedReference[] = [];
  for (const record of manifest.problems) {
    const referenceSgf = await readFile(path.join(projectRoot, record.sgfFile), "utf8");
    const referenceRoot = parseSgf(referenceSgf);
    references.push({
      record,
      fingerprint: canonicalProblemFingerprint(referenceRoot),
      rightShapes: canonicalRightShapes(referenceRoot),
    });
  }
  return { references };
}

export async function checkProblemDuplicates(
  sgf: string,
  root: SgfNode,
  corpus: DuplicateCorpus,
  options: {
    remote?: boolean;
    failThreshold?: number;
    manualReviewThreshold?: number;
    excludedIds?: number[];
  } = {},
): Promise<DuplicateReport> {
  const remoteEnabled = options.remote ?? true;
  const failThreshold = options.failThreshold ?? 90;
  const manualReviewThreshold = options.manualReviewThreshold ?? 80;
  const excludedIds = new Set(options.excludedIds ?? []);
  const candidateFingerprint = canonicalProblemFingerprint(root);
  const candidateShapes = canonicalRightShapes(root);

  let exactLocalMatch: DuplicateMatch | null = null;
  let closestLocalShape: LocalShapeMatch | null = null;

  for (const reference of corpus.references) {
    if (excludedIds.has(reference.record.id)) continue;
    if (reference.fingerprint === candidateFingerprint) {
      exactLocalMatch = {
        id: reference.record.id,
        sourceUrl: reference.record.sourceUrl,
      };
    }

    const score = Math.max(
      0,
      ...candidateShapes.flatMap((candidate) =>
        reference.rightShapes.map((referenceShape) => shapeSimilarity(candidate, referenceShape)),
      ),
    );
    const percentage = Math.round(score * 10_000) / 100;
    if (!closestLocalShape || percentage > closestLocalShape.percentage) {
      closestLocalShape = {
        id: reference.record.id,
        sourceUrl: reference.record.sourceUrl,
        percentage,
      };
    }
  }

  let remote: RemoteDuplicateReport = {
    status: "not_run",
    radiusTwoMatches: [],
    topPercentage: null,
    topMatchId: null,
    error: null,
  };

  if (remoteEnabled) {
    try {
      const response = await findSimilarProblems(sgf, {
        excludedIds: [...excludedIds],
        limit: 20,
      });
      const radiusTwoMatches = response.radiusTwo.entries.map(({ id, difficulty, createdAt }) => ({
        id,
        difficulty,
        createdAt,
      }));
      const topPercentage = response.percentage.topPercentage ?? 0;
      const topMatchId = response.percentage.entries[0]?.id ?? null;
      remote = {
        status:
          radiusTwoMatches.length || topPercentage >= failThreshold
            ? "fail"
            : topPercentage >= manualReviewThreshold
              ? "manual_review"
              : "pass",
        radiusTwoMatches,
        topPercentage,
        topMatchId,
        error: null,
      };
    } catch (error) {
      remote = {
        status: "error",
        radiusTwoMatches: [],
        topPercentage: null,
        topMatchId: null,
        error: error instanceof Error ? error.message : "The remote duplicate check failed.",
      };
    }
  }

  let status: DuplicateReport["status"] = "pass";
  if (exactLocalMatch || remote.status === "fail") status = "fail";
  else if (
    (closestLocalShape?.percentage ?? 0) >= manualReviewThreshold ||
    remote.status === "manual_review"
  ) {
    status = "manual_review";
  } else if (!remoteEnabled || remote.status === "error") {
    status = "not_run";
  }

  return { status, exactLocalMatch, closestLocalShape, remote };
}
