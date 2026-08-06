# Benchmark runs

Create a complete run with a model through an authenticated command-line harness:

```bash
python benchmark.py run --model <openai-model-id>
python benchmark.py run --harness claude --model <anthropic-model-id>
python benchmark.py run --harness grok --model <xai-model-id>
python benchmark.py run --harness opencode --model <provider>/<model-id>
```

The runner creates one auditable directory here, gives the selected CLI only the snapshotted benchmark packet, captures its event stream, evaluates the ten named SGF outputs by default, and refreshes the data used by the web UI. The input snapshot and generated outputs are immutable; the human evaluation record can be completed later. Web search and subprocess network access are disabled for the model. Remote GoProblems duplicate checks run afterward by default.

Useful maintenance commands:

```bash
python benchmark.py evaluate runs/<run-id>
python benchmark.py evaluate runs/<run-id> --local-only
python benchmark.py index
```

Windows/WSL shared checkouts are supported. The Python runner selects a Node.js
22+ executable that matches the platform-specific packages in `node_modules`;
`TSUMEGO_NODE` can override the detected executable.

Do not repair generated files in place. A repair or retry is a separate run with its own attempt metadata.
