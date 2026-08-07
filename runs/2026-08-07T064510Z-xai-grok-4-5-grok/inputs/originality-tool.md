# Originality query tool

The benchmark exposes one narrowly scoped tool for checking a completed candidate against the other generated files, the supplied local corpus, and the GoProblems database. General web and network access remain disabled.

## Before querying

The candidate must be parseable SGF. Built-in common-position checks run first and compare only the initial `AB`/`AW` setup across board symmetries and color reversal. A built-in match returns `duplicate` immediately without inspecting paths or contacting GoProblems.

If no built-in setup matches, the candidate must contain at least one accepted solution endpoint marked with uppercase `RIGHT` inside `C[...]`. GoProblems duplicate detection depends on a solution path, so an otherwise unmatched problem without `RIGHT` returns `invalid` with the error code `missing-right`, does not contact GoProblems, and still uses one query from the run budget.

## Submit a request

1. Finish writing the candidate under `outputs/`.
2. Choose a new request ID that has not appeared in `originality/requests/`.
3. Write `originality/requests/<request-id>.json` containing:

```json
{
  "requestId": "problem-01-final",
  "path": "outputs/problem-01.sgf"
}
```

4. Read `originality/results/<request-id>.json`. The result may take a short time to appear. Do not overwrite or reuse an earlier request ID.

The live budget and current usage are recorded in `originality/summary.json`. Every submitted request that is within the budget consumes one query, including malformed or structurally invalid candidates. Requests after the budget is exhausted return `quota_exceeded`.

## Interpret the result

- `clear`: no blocking or review-level match was found. This is the only acceptable final status.
- `review`: similarity is high enough that originality is uncertain. Replace or materially redesign the problem.
- `duplicate`: a built-in common setup, canonical local problem, same-run problem, radius-2 signature, or 90%+ full-corpus match was found. Replace the problem.
- `invalid`: the candidate cannot be checked. Correct every reported error before trying again.
- `unavailable`: the GoProblems checks could not be completed. A final candidate is not verified; retry later if budget remains.
- `quota_exceeded`: no query budget remains.

The response includes `candidateSha256`. A result applies only to the exact candidate contents checked. Any later edit invalidates it.

After all requested problems exist, submit one final query for every file. Do not edit a file after its final `clear` result. The benchmark independently checks the final files after generation and verifies that each final file hash received a `clear` tool result.
