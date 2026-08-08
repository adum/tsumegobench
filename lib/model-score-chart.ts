import {
  difficultyCappedHumanScore,
  type ReviewProgressFields,
} from "./review-progress";

export interface ModelMetadataEntry {
  id: string;
  displayName: string;
  family: string;
  releaseDate: string;
  icon: string;
  aliases: Array<{
    provider: string;
    name: string;
  }>;
}

export interface ModelMetadataFile {
  schemaVersion: number;
  models: ModelMetadataEntry[];
}

export interface IndexedRunForChart {
  runId: string;
  createdAt: string;
  model: {
    provider: string;
    name: string;
  };
  condition?: {
    problemCount?: number;
  };
  problems: Array<{
    reviews?: ReviewProgressFields[];
  }>;
}

export interface ModelScorePoint {
  id: string;
  displayName: string;
  family: string;
  releaseDate: string;
  icon: string;
  score: number;
  passedProblems: number;
  problemCount: number;
  runCount: number;
  bestRunId: string;
  bestRunCreatedAt: string;
}

export interface ModelScoreChartData {
  schemaVersion: 1;
  scoreScale: {
    minimum: 0;
    maximum: 10;
  };
  models: ModelScorePoint[];
  unmatchedModels: string[];
}

export function rankModelScoresForLegend<
  T extends Pick<ModelScorePoint, "displayName" | "score">,
>(models: readonly T[]): T[] {
  return [...models].sort(
    (left, right) =>
      right.score - left.score ||
      left.displayName.localeCompare(right.displayName),
  );
}

function modelKey(provider: string, name: string) {
  return `${provider.trim().toLowerCase()}/${name.trim().toLowerCase()}`;
}

function normalizedRunScore(run: IndexedRunForChart) {
  const configuredCount = Number(run.condition?.problemCount);
  const problemCount =
    Number.isFinite(configuredCount) && configuredCount > 0
      ? configuredCount
      : run.problems.length;
  const passedProblems = difficultyCappedHumanScore(run.problems).creditedProblems;
  const score = problemCount > 0
    ? Math.min(10, Math.round((passedProblems / problemCount) * 100) / 10)
    : 0;

  return { passedProblems, problemCount, score };
}

export function buildModelScoreChartData(
  runs: IndexedRunForChart[],
  metadata: ModelMetadataFile,
): ModelScoreChartData {
  const metadataByAlias = new Map<string, ModelMetadataEntry>();
  for (const model of metadata.models) {
    for (const alias of model.aliases) {
      metadataByAlias.set(modelKey(alias.provider, alias.name), model);
    }
  }

  const unmatchedModels = new Set<string>();
  const aggregates = new Map<
    string,
    {
      metadata: ModelMetadataEntry;
      runCount: number;
      best: ReturnType<typeof normalizedRunScore> & {
        runId: string;
        createdAt: string;
      };
    }
  >();

  for (const run of runs) {
    const runKey = modelKey(run.model.provider, run.model.name);
    const model = metadataByAlias.get(runKey);
    if (!model) {
      unmatchedModels.add(runKey);
      continue;
    }

    const result = normalizedRunScore(run);
    const existing = aggregates.get(model.id);
    const isBetter =
      !existing ||
      result.score > existing.best.score ||
      (result.score === existing.best.score && run.createdAt > existing.best.createdAt);

    if (!existing) {
      aggregates.set(model.id, {
        metadata: model,
        runCount: 1,
        best: { ...result, runId: run.runId, createdAt: run.createdAt },
      });
    } else {
      existing.runCount += 1;
      if (isBetter) {
        existing.best = { ...result, runId: run.runId, createdAt: run.createdAt };
      }
    }
  }

  const models = [...aggregates.values()]
    .map(({ metadata: model, runCount, best }) => ({
      id: model.id,
      displayName: model.displayName,
      family: model.family,
      releaseDate: model.releaseDate,
      icon: model.icon,
      score: best.score,
      passedProblems: best.passedProblems,
      problemCount: best.problemCount,
      runCount,
      bestRunId: best.runId,
      bestRunCreatedAt: best.createdAt,
    }))
    .sort(
      (left, right) =>
        left.releaseDate.localeCompare(right.releaseDate) ||
        left.displayName.localeCompare(right.displayName),
    );

  return {
    schemaVersion: 1,
    scoreScale: { minimum: 0, maximum: 10 },
    models,
    unmatchedModels: [...unmatchedModels].sort(),
  };
}
