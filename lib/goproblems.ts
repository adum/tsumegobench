const API_BASE = "https://www.goproblems.com/api/v2";

export interface SimilarProblem {
  id: number;
  difficulty: string;
  createdAt: string;
  matchPercentage: number | null;
  rank?: { value: number; unit: string; exact: boolean; mark: boolean };
}

export interface SimilarResponse {
  signatures?: string[];
  entries: SimilarProblem[];
  totalRecords: number;
}

export interface PercentageResponse extends SimilarResponse {
  topPercentage: number;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`GoProblems returned ${response.status}: ${detail.slice(0, 300)}`);
  }
  return (await response.json()) as T;
}

export async function findSimilarProblems(
  sgf: string,
  options: { excludedIds?: number[]; limit?: number } = {},
) {
  const excludedIds = options.excludedIds ?? [];
  const limit = options.limit ?? 20;
  const radiusTwo = await postJson<SimilarResponse>("/problems/similar", {
    pattern: sgf,
    radii: [2],
    excludedIds,
    limit,
  });

  const percentage = await postJson<PercentageResponse>(
    "/problems/similar-percentage",
    {
      pattern: sgf,
      excludedIds,
      limit,
    },
  );

  return { radiusTwo, percentage };
}
