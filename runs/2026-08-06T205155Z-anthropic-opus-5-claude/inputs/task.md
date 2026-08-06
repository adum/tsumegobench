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
4. Each output file must contain only one complete SGF collection—no Markdown fences or explanatory prose.
5. Do not modify anything under `inputs/`, `logs/`, or `evaluation/`, and do not modify `run.json`.
6. Do not access the web or any network service. Duplicate checks are performed by the benchmark after you exit.
7. Do not run the benchmark evaluator yourself. Finish all 10 files, verify them locally as far as you can, then exit.

Do not ask the operator questions and do not wait for repair feedback.
