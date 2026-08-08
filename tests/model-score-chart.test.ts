import assert from "node:assert/strict";
import test from "node:test";
import {
  buildModelScoreChartData,
  rankModelScoresForLegend,
  type IndexedRunForChart,
  type ModelMetadataFile,
} from "../lib/model-score-chart";

const metadata: ModelMetadataFile = {
  schemaVersion: 1,
  models: [
    {
      id: "example-model",
      displayName: "Example Model",
      family: "Example Lab",
      releaseDate: "2026-07-09",
      icon: "/provider-icons/openai.svg",
      aliases: [
        { provider: "example", name: "example-model" },
        { provider: "example", name: "example-model-alias" },
      ],
    },
  ],
};

function reviewedProblems(
  passing: number,
  total: number,
  difficulty = "5-9 kyu",
) {
  return Array.from({ length: total }, (_, index) => ({
    reviews: [
      {
        status: "completed" as const,
        valid: index < passing,
        realistic: true,
        duplicate: false,
        wellPathed: true,
        estimatedDifficulty: index < passing ? difficulty : null,
      },
    ],
  }));
}

function run(
  runId: string,
  model: string,
  passing: number,
  total: number,
  createdAt: string,
  difficulty?: string,
): IndexedRunForChart {
  return {
    runId,
    createdAt,
    model: { provider: "example", name: model },
    condition: { problemCount: total },
    problems: reviewedProblems(passing, total, difficulty),
  };
}

test("chart groups model aliases and keeps the best normalized score", () => {
  const chart = buildModelScoreChartData(
    [
      run("five-of-five", "example-model", 5, 5, "2026-08-01T00:00:00Z"),
      run("nine-of-ten", "example-model-alias", 9, 10, "2026-08-02T00:00:00Z"),
    ],
    metadata,
  );

  assert.equal(chart.models.length, 1);
  assert.equal(chart.models[0].score, 10);
  assert.equal(chart.models[0].bestRunId, "five-of-five");
  assert.equal(chart.models[0].runCount, 2);
});

test("chart reports models that do not yet have release metadata", () => {
  const chart = buildModelScoreChartData(
    [run("unknown", "unknown-model", 0, 10, "2026-08-03T00:00:00Z")],
    metadata,
  );

  assert.deepEqual(chart.models, []);
  assert.deepEqual(chart.unmatchedModels, ["example/unknown-model"]);
});

test("chart caps passing problems in the two easiest difficulty ranges", () => {
  const chart = buildModelScoreChartData(
    [
      run(
        "ten-easy-problems",
        "example-model",
        10,
        10,
        "2026-08-04T00:00:00Z",
        "20-30 kyu",
      ),
    ],
    metadata,
  );

  assert.equal(chart.models[0].passedProblems, 2);
  assert.equal(chart.models[0].score, 2);
});

test("chart legend ranks models from best to worst with stable alphabetical ties", () => {
  const models = [
    { displayName: "Zero Zeta", score: 0 },
    { displayName: "Winner", score: 4 },
    { displayName: "Zero Alpha", score: 0 },
    { displayName: "Runner-up", score: 2 },
  ];

  assert.deepEqual(
    rankModelScoresForLegend(models).map((model) => model.displayName),
    ["Winner", "Runner-up", "Zero Alpha", "Zero Zeta"],
  );
  assert.deepEqual(
    models.map((model) => model.displayName),
    ["Zero Zeta", "Winner", "Zero Alpha", "Runner-up"],
  );
});
