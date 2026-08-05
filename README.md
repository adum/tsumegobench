# Tsumego Bench

Tsumego Bench is a small, reproducible benchmark for a narrow question:

> Can an AI create **original, simple, standard life-and-death Go problems** with legal positions and complete, well-terminated SGF solution and refutation trees?

The repository combines a curated reference corpus, a strict SGF validator, local and GoProblems-powered duplicate detection, a controlled model prompt, a scoring rubric, and an interactive board/solution-tree reviewer.

## What is in the project

- `examples/canonical-life-and-death/` — 20 SGF reference problems, all explicitly on 19×19 boards, with four examples in each of five bands from 20–30 kyu through 1 dan. Every item was verified through the GoProblems API as canonical, standard, and life-and-death when synchronized. Source root instructions are removed so each position is presented only by its board shape and first-move color.
- `examples/manifest.json` — provenance, rank, author, source, rating, and original URL for every reference.
- `docs/authoring-guide.md` — the benchmark's concise definition of a good problem.
- `docs/model-prompt.md` — the controlled prompt to give each model.
- `docs/benchmark-spec.md` — run structure, acceptance gates, and comparison protocol.
- `docs/evaluation-rubric.md` — the human review scorecard.
- `scripts/` — corpus synchronization, validation, and duplicate checks.
- `benchmark.py` — creates a reproducible run, invokes an OpenAI model through Codex CLI, evaluates its files, and rebuilds the web index.
- `runs/` — checked-in model runs with input snapshots, generated SGFs, logs, and structured evaluation records.
- The web reviewer — browse each problem, replay any variation, and inspect the graphical solution tree.

## Quick start

```bash
npm install
npm run dev
```

Open the local address printed by the development server.

Run a benchmark with an OpenAI model available to your authenticated Codex CLI:

```bash
python benchmark.py run --model <openai-model-id>
```

The evaluator requires Node.js 22 or newer. When the checkout is shared between
Windows and WSL, the runner automatically uses a compatible Windows Node runtime
for Windows-installed dependencies. Set `TSUMEGO_NODE` only if you need to
override that selection.

If Codex rejects an unknown, inaccessible, or unsupported model ID, the runner
prints the rejection and exits immediately. It does not retain a run directory,
evaluate empty outputs, or add the attempt to the web index.

Add `--reasoning-effort high` when you want to pin an exposed Codex reasoning setting, or `--local-only` to skip the post-run GoProblems API checks. The runner disables model web and network access, captures the CLI event log automatically, and writes the five candidate SGFs under `runs/<run-id>/outputs/`.

Validate the reference set or a submission:

```bash
npm run validate
npm run validate -- runs/my-run/outputs
```

Check one candidate for duplicates locally and against GoProblems:

```bash
npm run duplicates -- runs/my-run/outputs/problem-01.sgf
```

The remote duplicate gate fails on any radius-2 solution-signature match or a percentage match at or above 90%. Use `--local-only`, `--threshold=95`, or `--exclude-id=18843` when appropriate.

Refresh the public reference data deliberately—not as part of a normal build:

```bash
npm run sync:examples
```

The synchronizer spaces its requests and verifies the corpus contract before writing files. Please follow the GoProblems request not to call its API excessively.

## Benchmark in one pass

1. Invoke `python benchmark.py run --model <openai-model-id>` from an authenticated Codex CLI environment.
2. The runner snapshots the controlled inputs and asks Codex to write five SGFs directly into the run directory.
3. It preserves the Codex event log and runs structural and duplicate checks automatically.
4. Browse the checked-in run and its generated problems in the web viewer.
5. Have a competent Go player review life/death correctness and tree completeness.
6. Complete `evaluation/human.json` using `docs/evaluation-rubric.md`; report both the mean score and acceptance rate.

Structural validity and originality are hard gates. A beautiful but duplicated problem, or a novel position with a broken solution tree, is not an accepted result.

## Source guidance

The contract is derived from GoProblems' public guidance:

- [Types of Problems](https://www.goproblems.com/article/problemtypes)
- [Problem Construction Basics](https://www.goproblems.com/article/constructionbasics)
- [Problem Construction Best Practices](https://www.goproblems.com/article/bestpractices)
- [API access](https://www.goproblems.com/article/api)
- [Solution Signatures](https://www.goproblems.com/article/solutionsignatures)

The reference SGFs remain attributed to their listed GoProblems authors and sources. They are included as benchmark examples and provenance is retained in `examples/manifest.json`.
