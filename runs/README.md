# Benchmark runs

Create a complete run with an OpenAI model through the authenticated Codex CLI:

```bash
python benchmark.py run --model <openai-model-id>
```

The runner creates one auditable directory here, gives Codex only the snapshotted benchmark packet, captures the CLI event stream, evaluates the five named SGF outputs, and refreshes the data used by the web UI. The input snapshot and generated outputs are immutable; the human evaluation record can be completed later. Web search and subprocess network access are disabled for the model. Remote GoProblems duplicate checks run afterward by default.

Useful maintenance commands:

```bash
python benchmark.py evaluate runs/<run-id>
python benchmark.py evaluate runs/<run-id> --local-only
python benchmark.py index
```

Do not repair generated files in place. A repair or retry is a separate run with its own attempt metadata.
