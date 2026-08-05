import assert from "node:assert/strict";
import test from "node:test";
import problemData from "../app/data/problems.generated.json";

interface ProblemRecord {
  id: number;
  rankValue: number;
  rankUnit: string;
  canonical: boolean;
  standard: boolean;
}

const problems = problemData as ProblemRecord[];

function difficultyBand(problem: ProblemRecord) {
  if (problem.rankUnit === "dan" && problem.rankValue === 1) return "1 dan";
  if (problem.rankUnit !== "kyu") return "outside";
  if (problem.rankValue >= 20 && problem.rankValue <= 30) return "20-30 kyu";
  if (problem.rankValue >= 10 && problem.rankValue <= 19) return "10-19 kyu";
  if (problem.rankValue >= 5 && problem.rankValue <= 9) return "5-9 kyu";
  if (problem.rankValue >= 1 && problem.rankValue <= 4) return "1-4 kyu";
  return "outside";
}

test("reference corpus is evenly distributed from 30 kyu through 1 dan", () => {
  assert.equal(problems.length, 20);
  assert.equal(new Set(problems.map((problem) => problem.id)).size, 20);
  assert.ok(problems.every((problem) => problem.canonical && problem.standard));

  const counts = Object.fromEntries(
    ["20-30 kyu", "10-19 kyu", "5-9 kyu", "1-4 kyu", "1 dan"].map((band) => [
      band,
      problems.filter((problem) => difficultyBand(problem) === band).length,
    ]),
  );

  assert.deepEqual(counts, {
    "20-30 kyu": 4,
    "10-19 kyu": 4,
    "5-9 kyu": 4,
    "1-4 kyu": 4,
    "1 dan": 4,
  });
});
