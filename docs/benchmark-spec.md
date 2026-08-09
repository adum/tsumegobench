# Benchmark specification

## Objective

Measure whether a model can synthesize useful, original, simple life-and-death problems—not merely emit parseable SGF or remix a known position.

The default task is **ten problems per run**. Ten provides two suggested targets in each of five bands, exposing consistency failures while keeping expert review practical. Those targets encourage a range, while the final score uses the human-estimated difficulty caps below. The runner accepts `--count` values from 5 through 50 for explicitly labeled alternate conditions.

## Controlled inputs

Every compared model receives:

1. The generated command-line task in `inputs/task.md`.
2. The exact snapshot of `docs/model-prompt.md`.
3. The same authoring guide, reference manifest, and 20 reference SGFs.
4. No conversation history or repair feedback on the first attempt.

Every candidate must explicitly declare a 19×19 board with `SZ[19]`. Other board sizes and omitted `SZ` properties fail structural validation.

The supported harnesses are non-interactive `codex exec` for OpenAI models, Claude CLI print mode for Anthropic models, Grok CLI headless mode for xAI models, and OpenCode CLI `run` mode for models addressed as `provider/model`. Codex receives workspace-write access only inside the run directory, with web search and subprocess network access disabled. Claude Code 2.1.217 or newer runs in safe mode, which disables ordinary user and project instructions, skills, plugins, hooks, and MCP configuration; on-disk session persistence and Chrome are also disabled. Its built-in tools are restricted to `Read`, `Write`, `Edit`, `Glob`, and `Grep`, while shell, web, and MCP tools are explicitly denied. Its live process uses streaming JSON input so multiple benchmark continuation turns share one in-memory conversation. Grok runs with its strict sandbox and a prompt-file snapshot, with automatic updates, plan mode, subagents, memory, shell, web, and MCP tools disabled; the remaining file tools are auto-approved so the headless process can write outputs without operator interaction. OpenCode 1.1.1 or newer runs with a snapshotted configuration, external plugins disabled, sharing and updates disabled, and only read, edit, glob, grep, and list permissions allowed; shell, web, MCP, LSP, skills, questions, external directories, and subagents are denied. Its JSON event stream records the session, final response, per-step token usage, and cost when available. Record the provider, exact model identifier, harness and version, date, effort setting, command, duration, token usage when reported, and exit status.

Claude uses an in-session continuation loop. Turn one receives the complete task. After each result event, the runner checks the run directory and sends a compact continuation message only when expected outputs remain. The message reports present and missing filenames plus shared originality-query usage, but deliberately assigns no fixed problem or batch: Claude may carry analysis forward and create or revise any number of problems per turn. The loop stops when all requested, correctly named SGFs exist, after 20 turns, or after three consecutive turns without SGF or query progress. Output-limit results are continuation boundaries rather than immediate permanent failures. The runner sets `CLAUDE_CODE_MAX_OUTPUT_TOKENS` to 128,000, records every input and output event, and aggregates usage across result events. All turns in one invocation remain inside one live, non-persistent Claude process and share one context. If that process reports a session limit with a reset time, the runner preserves the active SGFs and shared originality state, waits until the reset plus a one-minute grace period, then launches a fresh isolated Claude process with the full task and an explicit summary of present and missing files. This pause does not consume a transient retry attempt. Continuation turns, reset pauses, and fresh post-reset sessions all remain within the shared 12-hour model-phase timeout.

OpenCode uses a separate outer continuation loop because one `opencode run` session can end at a model-response length boundary before completing the file set. Each successful round starts a fresh OpenCode session in the same run directory. Round one receives the complete task; later rounds receive the missing expected filenames and are told to reread `inputs/task.md`. The loop stops after all requested, correctly named SGFs exist or after 20 completed rounds, without treating a transient transport retry as another round. All rounds share one originality-query budget and one 12-hour model-phase timeout. The runner sets OpenCode's per-response output ceiling to 65,536 tokens. Codex and Grok retain their single-session behavior.

The runner also starts a file-based originality broker. It is the only process allowed to contact GoProblems; the model still has no general network access. The broker accepts at most five queries per requested problem by default. It first rejects hard-coded common initial setups locally across board symmetries and color reversal, without inspecting their paths or making an API request. All other candidates require at least one `RIGHT` path before the GoProblems checks can run. The broker records every response and exposes only compact similarity metadata. The condition records the exact query limit and tool version. The post-run evaluator independently repeats the duplicate checks on the final files.

## Run layout

```text
runs/
  2026-08-05T120000Z-openai-model-codex/
    run.json
    inputs/
      task.md
      model-prompt.md
      authoring-guide.md
      benchmark-spec.md
      reference-manifest.json
      examples/*.sgf
      opencode-config/opencode.json  # OpenCode runs only
    outputs/
      problem-01.sgf
      problem-02.sgf
      problem-03.sgf
      problem-04.sgf
      problem-05.sgf
      problem-06.sgf
      problem-07.sgf
      problem-08.sgf
      problem-09.sgf
      problem-10.sgf
    logs/
      claude-input.jsonl          # Claude runs only
      <harness>-events.jsonl
      <harness>-stderr.txt
      final-message.txt
    evaluation/
      automated.json
      human.json
      results.json
```

The Python runner creates this structure, snapshots and hashes every input, invokes the selected CLI harness, captures its logs, evaluates whatever files exist at process exit, and rebuilds the web index. Claude run IDs use the parallel `...-anthropic-<model>-claude` form, Grok run IDs use `...-xai-<model>-grok`, and OpenCode run IDs use `...-<provider>-<model>-opencode`. Claude's same-session turns and OpenCode's outer rounds each constitute one original model attempt; preserve the final files produced when either policy stops. Any subsequent operator or repair-agent changes belong in a new, explicitly labeled run rather than silently replacing that result.

## Acceptance pipeline

```text
raw output
  → parse and structural validation
  → local exact/transformed duplicate check
  → GoProblems radius-2 and percentage check
  → expert life/death and tree review
  → rubric score
```

### Hard gates

A candidate is rejected before scoring if any of these is true:

- It is not parseable SGF.
- A structural validator error remains.
- It contains a root comment or written problem instruction.
- It does not explicitly declare `SZ[19]` at the root.
- The position or any required line is illegal.
- The claimed `RIGHT` outcome is false.
- A materially correct alternative is missing or marked wrong.
- A strongest or materially distinct defense is missing, so an accepted solution is not established under best resistance.
- A correct or refutation path ends before its claimed result is forced and clear.
- It matches the local exact/transformed fingerprint of a reference.
- GoProblems returns any radius-2 solution-signature match.
- The top GoProblems percentage match is at least 90% under the default policy.

Rejected candidates receive 0 points but remain part of the run's acceptance-rate denominator.

During human tree review, inspect both directions at every meaningful branch: all materially correct solver choices must be accepted, and all accepted choices must survive the strongest relevant defenses. Plausible wrong choices should include the opponent reply that actually establishes the refutation. Review endpoints separately from move correctness; penalize both premature stopping and unnecessary cleanup, using the reference SGFs as the calibration set.

### Human difficulty credit

The model's target or self-estimate never determines scored difficulty. A human reviewer must assign a difficulty range to every otherwise valid problem before it can receive final-score credit. Count human-passed problems by their reviewed range, then apply these caps:

- At most two 20–30 kyu problems receive credit.
- At most two additional 10–19 kyu problems receive credit.
- Every problem rated 5–9 kyu or harder may receive credit, with no cap on those harder ranges.

Problems above 1 dan are allowed. A varied set among the uncapped harder problems is preferred, but it is not enforced by another cap. When reviewers disagree, use the easiest submitted range so disagreement cannot inflate the score. A passing problem without a difficulty estimate receives no credit until the review is completed.

### Manual-review band

A top percentage match of 80–89%, a local solution-shape overlap of 80% or more, or a strong visual resemblance is held for side-by-side review. The reviewer records why the tactical idea and construction are materially distinct before accepting it.

## Reporting

For each run, report:

- Difficulty-capped, human-passed problems / requested problem count (primary reliability metric)
- Mean score across the full requested set, counting rejected candidates as 0 (primary quality metric)
- Mean score among accepted candidates (conditional quality)
- Structural pass rate
- Originality pass rate
- Median manual review time

Do not rank models only by their best problem. The benchmark is intended to measure reliable creation.

## Repeated trials

For a serious comparison, run at least three independent ten-problem trials per model. Keep the problem count, prompts, and tool access fixed within a condition. Report mean and range; do not pool repaired and unrepaired runs.

## Current limitation

The first version automates SGF structure, board legality checks, local transformed fingerprints, and GoProblems similarity queries. It does **not** prove life/death truth. Semantic correctness and completeness still require a competent Go reviewer (or a separately documented engine-assisted protocol). That distinction is intentional: parseability is not the same as a sound tsumego.
