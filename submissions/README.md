# Submissions

Create one directory per model run. Keep first-attempt outputs immutable so repaired SGFs cannot be confused with zero-shot results.

```text
submissions/<date>-<model>-<condition>/
  run.json
  problem-01.sgf
  problem-02.sgf
  problem-03.sgf
  problem-04.sgf
  problem-05.sgf
```

Start from `submissions/run.example.json`. Validate the directory with `npm run validate -- submissions/<run>` and run `npm run duplicates -- <file>` for each accepted structural candidate.

Every submitted SGF must explicitly declare a 19×19 board with `SZ[19]` at the root.
