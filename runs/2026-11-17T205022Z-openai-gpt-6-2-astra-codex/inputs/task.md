# Tsumego Bench execution task

This is a controlled benchmark run. Work only inside the current run directory.

1. Read `inputs/model-prompt.md` in full and follow it exactly.
2. Use `inputs/authoring-guide.md`, `inputs/reference-manifest.json`, and all SGFs in `inputs/examples/` as the supplied reference material.
3. Create exactly 10 final candidate SGF files using these names and target difficulties:
   - `outputs/problem-01.sgf` - target difficulty: 20-30 kyu
   - `outputs/problem-02.sgf` - target difficulty: 20-30 kyu
   - `outputs/problem-03.sgf` - target difficulty: 10-19 kyu
   - `outputs/problem-04.sgf` - target difficulty: 10-19 kyu
   - `outputs/problem-05.sgf` - target difficulty: 5-9 kyu
   - `outputs/problem-06.sgf` - target difficulty: 5-9 kyu
   - `outputs/problem-07.sgf` - target difficulty: 1-4 kyu
   - `outputs/problem-08.sgf` - target difficulty: 1-4 kyu
   - `outputs/problem-09.sgf` - target difficulty: about 1 dan
   - `outputs/problem-10.sgf` - target difficulty: about 1 dan
   These targets are guidance for producing a useful range, not score caps on harder work. Human reviewers determine actual difficulty. In the final score, at most two valid 20-30 kyu problems and at most two valid 10-19 kyu problems receive credit; every valid problem rated 5-9 kyu or harder can receive credit. Problems harder than 1 dan are allowed. Aim to spread the harder problems across multiple levels rather than clustering them all at one difficulty.
4. Each output file must contain only one complete SGF collection—no Markdown fences or explanatory prose.
5. Do not modify anything under `inputs/`, `logs/`, `evaluation/`, or `originality/results/`; do not modify `originality/summary.json` or `run.json`. Under `originality/`, you may only create new request files in `originality/requests/`.
6. Read `inputs/originality-tool.md`. The originality query budget is 50 requests (5 per requested problem). Built-in common setups can return `duplicate` from the initial stones alone; otherwise, a request without at least one `C[RIGHT]` endpoint returns `invalid`. Either outcome still consumes one query.
7. Use the originality tool while authoring, then query every exact final output again after all 10 files exist. Only a final `clear` result is acceptable. Do not edit a file after its final clear result.
8. Do not access the web or any other network service. The file-based originality tool is the only permitted external lookup.
9. Do not run the benchmark evaluator yourself. Finish all 10 files, verify them, then exit.

Do not ask the operator questions and do not wait for repair feedback.
