# Benchmark specification

## Objective

Measure whether a model can synthesize useful, original, simple life-and-death problems—not merely emit parseable SGF or remix a known position.

The default task is **ten problems per run**. Ten provides two targets in each of the five difficulty bands, exposing consistency failures while keeping expert review practical. The runner accepts `--count` values from 5 through 50 for explicitly labeled alternate conditions.

## Controlled inputs

Every compared model receives:

1. The generated command-line task in `inputs/task.md`.
2. The exact snapshot of `docs/model-prompt.md`.
3. The same authoring guide, reference manifest, and 20 reference SGFs.
4. No conversation history or repair feedback on the first attempt.

Every candidate must explicitly declare a 19×19 board with `SZ[19]`. Other board sizes and omitted `SZ` properties fail structural validation.

The supported harnesses are non-interactive `codex exec` for OpenAI models, Claude CLI print mode for Anthropic models, Grok CLI headless mode for xAI models, and OpenCode CLI `run` mode for models addressed as `provider/model`. Codex receives workspace-write access only inside the run directory, with web search and subprocess network access disabled. Claude Code 2.1.169 or newer runs in safe mode, which disables ordinary user and project instructions, skills, plugins, hooks, and MCP configuration; session persistence and Chrome are also disabled. Its built-in tools are restricted to `Read`, `Write`, `Edit`, `Glob`, and `Grep`, while shell, web, and MCP tools are explicitly denied. Grok runs with its strict sandbox and a prompt-file snapshot, with automatic updates, plan mode, subagents, memory, shell, web, and MCP tools disabled; the remaining file tools are auto-approved so the headless process can write outputs without operator interaction. OpenCode 1.1.1 or newer runs with a snapshotted configuration, external plugins disabled, sharing and updates disabled, and only read, edit, glob, grep, and list permissions allowed; shell, web, MCP, LSP, skills, questions, external directories, and subagents are denied. Its JSON event stream records the session, final response, per-step token usage, and cost when available. Record the provider, exact model identifier, harness and version, date, effort setting, command, duration, token usage when reported, and exit status.

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
      <harness>-events.jsonl
      <harness>-stderr.txt
      final-message.txt
    evaluation/
      automated.json
      human.json
      results.json
```

The Python runner creates this structure, snapshots and hashes every input, invokes the selected CLI harness, captures its logs, evaluates whatever files exist at process exit, and rebuilds the web index. Claude run IDs use the parallel `...-anthropic-<model>-claude` form, Grok run IDs use `...-xai-<model>-grok`, and OpenCode run IDs use `...-<provider>-<model>-opencode`. Preserve the model's first files exactly. If you repair a problem, save it as a new, explicitly labeled run; do not silently replace the first attempt.

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

### Manual-review band

A top percentage match of 80–89%, a local solution-shape overlap of 80% or more, or a strong visual resemblance is held for side-by-side review. The reviewer records why the tactical idea and construction are materially distinct before accepting it.

## Reporting

For each run, report:

- Accepted problems / requested problem count (primary reliability metric)
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
