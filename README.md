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
- `data/model-metadata.json` — normalized model names, family icons, and public release dates used by the home-page score chart.
- `benchmark.py` — creates a reproducible run, invokes a model through Codex CLI, Claude CLI, Grok CLI, or OpenCode CLI, evaluates its files, and rebuilds the web index.
- `runs/` — checked-in model runs with input snapshots, generated SGFs, logs, and structured evaluation records.
- The web reviewer — browse each problem, replay any variation, and inspect the graphical solution tree.

## Quick start

```bash
npm install
npm run dev
```

Open the local address printed by the development server.

Run a benchmark with an OpenAI model available to your authenticated Codex CLI (the default harness):

```bash
python benchmark.py run --model <openai-model-id>
```

Or run an Anthropic model through an authenticated Claude CLI:

```bash
python benchmark.py run --harness claude --model <claude-model-id-or-alias>
```

Or run an xAI model through an authenticated Grok CLI:

```bash
python benchmark.py run --harness grok --model <grok-model-id-or-alias>
```

Or run a provider/model combination available to an authenticated OpenCode CLI:

```bash
python benchmark.py run --harness opencode --model <provider>/<model-id>
```

Install and authenticate the selected CLI before running the benchmark. The runner finds `codex`
`claude`, `grok`, or `opencode` on `PATH`; use `--codex` / `CODEX_CLI`, `--claude` /
`CLAUDE_CLI`, `--grok` / `GROK_CLI`, or `--opencode` / `OPENCODE_CLI` to provide an explicit
executable. Prefer a full, versioned model ID over a moving alias when reproducibility matters.
OpenCode model names must use its exact `provider/model` form. Claude Code 2.1.169 or newer and
OpenCode 1.1.1 or newer are required for the isolated modes used by the benchmark. The runner checks
the version before creating a run; an obsolete or broken CLI exits without saving or evaluating
anything. See
Anthropic's [Claude Code installation guide](https://code.claude.com/docs/en/installation) or
xAI's [Grok Build guide](https://docs.x.ai/build/overview), or the
[OpenCode installation guide](https://opencode.ai/docs) for installation and authentication.

OpenCode generation uses fresh outer rounds against the same run directory. It stops as soon as all
requested, correctly named SGF files exist, or after 20 completed OpenCode rounds. Later rounds receive
the missing filename list and continue from files already written; the originality-query budget remains
shared across the whole benchmark run. Each OpenCode model response is allowed up to 65,536 output and
reasoning tokens through `OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX`. The normal `--timeout` remains the
wall-clock limit for the entire model phase across every round and retry.

The evaluator requires Node.js 22 or newer. When the checkout is shared between
Windows and WSL, the runner automatically uses a compatible Windows Node runtime
for Windows-installed dependencies. Set `TSUMEGO_NODE` only if you need to
override that selection.

If the selected CLI rejects an unknown, inaccessible, or unsupported model ID, the runner
prints the rejection and exits immediately. It does not retain a run directory,
evaluate empty outputs, or add the attempt to the web index.

Add `--reasoning-effort high` (or `--effort high`) when you want to pin an effort setting exposed by the selected CLI. For OpenCode, the effort value is passed as the model's provider-specific `--variant`. The runner disables general model web and network tools, captures the selected CLI's event log automatically, and writes ten candidate SGFs under `runs/<run-id>/outputs/` by default. Use `--count <5-50>` only when you want an explicitly different benchmark condition. `--local-only` is a diagnostic mode that disables both the live originality tool and post-run GoProblems checks, so it cannot produce an originality-complete benchmark result.

When a run starts, the runner prints the selected reasoning effort. If the flag is omitted, it prints `CLI/model default`; the manifest records `null` because the benchmark did not request a specific level.

Recognized transient transport, rate-limit, and service failures are retried up to five times within each CLI round, with exponential backoff of 15, 30, 60, and 120 seconds. Model-selection, authentication, launch, and other permanent failures still fail immediately. Every invocation is recorded under `harness.attempts` in `run.json`, with full per-attempt logs under `logs/attempts/`. Other harnesses archive partial SGFs from a failed retryable attempt before retrying; OpenCode deliberately preserves them because its retries and outer rounds share one workspace. The final terminal report lists every attempt, duration, exit status, SGF count, and the total time spent waiting. Use `--max-attempts`, `--retry-base-delay`, or `--retry-max-delay` to override the retry defaults; all rounds, attempts, and waits remain within `--timeout` (12 hours by default).

Every normal run includes a file-based originality tool. The model receives five queries per requested problem by default—50 for the standard ten-problem run—and must spend one final query on each exact output. Built-in common setups are rejected locally from their initial stones alone, across board symmetries and color reversal, without an API call. Other queries require a structurally complete SGF with at least one `C[RIGHT]` solution endpoint; invalid queries return an error and still consume budget. The tool also checks other generated files, the local reference corpus, a radius-2 GoProblems solution signature, and an independent full-corpus percentage search. Use `--duplicate-query-limit` only when deliberately defining a different benchmark condition.

Validate the reference set or a submission:

```bash
npm run validate
npm run validate -- runs/my-run/outputs
```

Check one candidate for duplicates locally and against GoProblems:

```bash
npm run duplicates -- runs/my-run/outputs/problem-01.sgf
```

The remote duplicate gate fails on any radius-2 solution-signature match or a full-corpus percentage match at or above 90%. An 80–89% match requires review. Use `--local-only`, `--threshold=95`, or `--exclude-id=18843` only for diagnostic or corpus-maintenance work.

Refresh the public reference data deliberately—not as part of a normal build:

```bash
npm run sync:examples
```

The synchronizer spaces its requests and verifies the corpus contract before writing files. Please follow the GoProblems request not to call its API excessively.

## Human review

Launch the local review UI with:

```bash
python3 benchmark.py review
```

The command selects the most recently completed evaluated run, opens a local browser session, and saves every checkbox, difficulty, and star change automatically. A rejected problem is complete as soon as it is marked invalid; a valid problem needs a human-estimated difficulty before its review is complete and it can receive score credit. The 1–5 quality rating remains optional. Pass a run ID only when reviewing an older run:

```bash
python3 benchmark.py review 2026-08-05T225707Z-openai-gpt-5-6-luna-codex
```

For each problem, the initial review can record whether it is valid, whether the position is realistic, whether the reviewer considers it a duplicate, whether its solution and refutation paths are well formed, an estimated difficulty band for valid problems, and a 1–5 quality rating. Reviewer records are independent, so a second reviewer can assess the same run without overwriting the first review. The structured records live in `evaluation/reviews.json`; the hosted site remains read-only.

## Release-date score chart

The home page plots each normalized model once by public release date. Its score is the best difficulty-capped human-passed problem rate across that model's runs, normalized to 10 even when a nonstandard run size is used. At most two reviewed 20–30 kyu problems and two reviewed 10–19 kyu problems receive credit; reviewed problems rated 5–9 kyu or harder are uncapped. A valid problem without a human difficulty estimate receives no score credit. Equivalent model aliases are grouped by `data/model-metadata.json`.

The run index rebuilds the chart automatically. To rebuild only the chart after editing model metadata, run:

```bash
npm run chart:build
```

Models without release metadata are listed by the script and omitted from the chart until an entry is added.

## Benchmark in one pass

1. Invoke `python benchmark.py run --model <openai-model-id>` for Codex, add `--harness claude` for Claude CLI, add `--harness grok` for Grok CLI, or use `--harness opencode --model <provider>/<model-id>` for OpenCode CLI.
2. The runner snapshots the controlled inputs and asks the selected model to write ten SGFs directly into the run directory.
3. It preserves the selected CLI's event log and runs structural and duplicate checks automatically.
4. Run `python3 benchmark.py review`; it defaults to the run that just completed.
5. Have one or more competent Go players submit the basic validity, realism, duplicate, path quality, difficulty, and overall quality review in the browser.
6. Check in the resulting `evaluation/reviews.json` with the rest of the run. Use `docs/evaluation-rubric.md` when a deeper 100-point review is needed.

Structural validity and originality are hard gates. A beautiful but duplicated problem, or a novel position with a broken solution tree, is not an accepted result.

## Source guidance

The contract is derived from GoProblems' public guidance:

- [Types of Problems](https://www.goproblems.com/article/problemtypes)
- [Problem Construction Basics](https://www.goproblems.com/article/constructionbasics)
- [Problem Construction Best Practices](https://www.goproblems.com/article/bestpractices)
- [API access](https://www.goproblems.com/article/api)
- [Solution Signatures](https://www.goproblems.com/article/solutionsignatures)

The reference SGFs remain attributed to their listed GoProblems authors and sources. They are included as benchmark examples and provenance is retained in `examples/manifest.json`.
