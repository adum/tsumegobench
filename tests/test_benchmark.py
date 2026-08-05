import json
import tempfile
import unittest
from pathlib import Path

import benchmark


class BenchmarkRunnerTests(unittest.TestCase):
    def test_run_defaults_to_ten_problems(self):
        args = benchmark.build_parser().parse_args(["run", "--model", "gpt-test"])

        self.assertEqual(args.count, 10)
        self.assertEqual(
            benchmark.expected_output_names(args.count),
            [f"problem-{index:02d}.sgf" for index in range(1, 11)],
        )
        self.assertEqual(
            benchmark.difficulty_targets(args.count),
            [
                "20-30 kyu",
                "20-30 kyu",
                "10-19 kyu",
                "10-19 kyu",
                "5-9 kyu",
                "5-9 kyu",
                "1-4 kyu",
                "1-4 kyu",
                "about 1 dan",
                "about 1 dan",
            ],
        )

    def test_generated_task_lists_all_ten_default_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            benchmark.copy_inputs(run_dir, benchmark.DEFAULT_PROBLEM_COUNT)
            task = (run_dir / "inputs" / "task.md").read_text(encoding="utf-8")

        self.assertIn("Create exactly 10 final candidate SGF files", task)
        self.assertIn("`outputs/problem-01.sgf`", task)
        self.assertIn("`outputs/problem-10.sgf`", task)
        self.assertNotIn("problem-11.sgf", task)
        self.assertEqual(task.count("target difficulty:"), 10)

    def test_extracts_nested_codex_failure(self):
        upstream = {
            "type": "error",
            "status": 400,
            "error": {
                "type": "invalid_request_error",
                "message": "The 'made-up-model' model is not supported when using Codex.",
            },
        }
        events = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                json.dumps({"type": "error", "message": json.dumps(upstream)}),
                json.dumps({"type": "turn.failed", "error": {"message": json.dumps(upstream)}}),
            ]
        )

        parsed = benchmark.parse_codex_events(events)

        self.assertEqual(parsed["threadId"], "thread-1")
        self.assertEqual(
            parsed["failureMessage"],
            "The 'made-up-model' model is not supported when using Codex.",
        )

    def test_recognizes_model_selection_errors(self):
        self.assertTrue(
            benchmark.is_model_selection_failure(
                "The 'made-up-model' model is not supported when using Codex with a ChatGPT account."
            )
        )
        self.assertTrue(
            benchmark.is_model_selection_failure(None, "error: unsupported model identifier")
        )
        self.assertFalse(benchmark.is_model_selection_failure("The request timed out."))


if __name__ == "__main__":
    unittest.main()
