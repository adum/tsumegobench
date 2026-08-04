import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { parseSgf, visibleComment } from "../lib/sgf";

const PROBLEM_IDS = [
  18843, 10507, 39693, 53787, 53750, 52370, 52244, 52243, 51056, 49335,
  48940, 47734, 47732, 6208, 5844, 5973, 5943, 5922, 5920, 5849,
] as const;

const API_BASE = "https://www.goproblems.com/api/v2/problems";
const workspace = process.cwd();
const examplesDirectory = path.join(workspace, "examples", "canonical-life-and-death");
const appDataDirectory = path.join(workspace, "app", "data");

interface ProblemResponse {
  id: number;
  sgf: string;
  isCanon: boolean;
  isStandard: boolean;
  genre: string;
  specificGenre: string;
  playerColor: "black" | "white";
  rank: { value: number; unit: string; exact: boolean; mark: boolean };
  elo: number;
  author: { id: number; name: string };
  source: string;
  createdAt: string;
  rating: { stars: number; votes: number };
  attempts: { solved: number; failed: number; tries: number };
  avgSolveTimeSeconds: number;
}

const wait = (milliseconds: number) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

async function fetchProblem(id: number): Promise<ProblemResponse> {
  const response = await fetch(`${API_BASE}/${id}`, {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) throw new Error(`Problem ${id}: HTTP ${response.status}`);
  return (await response.json()) as ProblemResponse;
}

await mkdir(examplesDirectory, { recursive: true });
await mkdir(appDataDirectory, { recursive: true });

const records = [];
for (const [index, id] of PROBLEM_IDS.entries()) {
  const problem = await fetchProblem(id);
  if (!problem.isCanon || !problem.isStandard || problem.genre !== "life and death") {
    throw new Error(
      `Problem ${id} no longer meets the corpus contract (canonical + standard + life and death).`,
    );
  }

  const sgf = `${problem.sgf.replace(/\r\n/g, "\n").trim()}\n`;
  const fileName = `gp-${id}.sgf`;
  await writeFile(path.join(examplesDirectory, fileName), sgf, "utf8");
  const root = parseSgf(sgf);
  const instruction = visibleComment(root);

  records.push({
    id: problem.id,
    label: `Reference #${problem.id}`,
    instruction: instruction || "Find the best local result.",
    rank: `${problem.rank.value} ${problem.rank.unit}`,
    rankValue: problem.rank.value,
    rankUnit: problem.rank.unit,
    elo: Math.round(problem.elo),
    playerColor: problem.playerColor,
    genre: problem.specificGenre || problem.genre,
    author: problem.author.name,
    source: problem.source || "Not listed",
    createdAt: problem.createdAt,
    rating: problem.rating,
    attempts: problem.attempts,
    avgSolveTimeSeconds: problem.avgSolveTimeSeconds,
    canonical: problem.isCanon,
    standard: problem.isStandard,
    sourceUrl: `https://www.goproblems.com/problems/${problem.id}`,
    sgfFile: `examples/canonical-life-and-death/${fileName}`,
    sgf: sgf.trim(),
  });

  process.stdout.write(`synced ${id} (${index + 1}/${PROBLEM_IDS.length})\n`);
  if (index < PROBLEM_IDS.length - 1) await wait(150);
}

const manifest = {
  name: "Canonical life-and-death reference corpus",
  description:
    "Public GoProblems examples verified as canonical, standard, and life-and-death when synchronized.",
  source: "https://www.goproblems.com",
  sourceGuidance: [
    "https://www.goproblems.com/article/problemtypes",
    "https://www.goproblems.com/article/constructionbasics",
    "https://www.goproblems.com/article/bestpractices",
  ],
  count: records.length,
  problems: records.map(({ sgf, ...record }) => {
    void sgf;
    return record;
  }),
};

await writeFile(
  path.join(workspace, "examples", "manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
  "utf8",
);
await writeFile(
  path.join(appDataDirectory, "problems.generated.json"),
  `${JSON.stringify(records, null, 2)}\n`,
  "utf8",
);

process.stdout.write(`Wrote ${records.length} verified reference problems.\n`);
