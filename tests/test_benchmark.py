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

    def test_review_defaults_to_the_newest_completed_evaluated_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            for run_id, status, completed_at, evaluated in [
                ("older", "completed", "2026-08-05T10:00:00Z", True),
                ("newest", "completed", "2026-08-05T12:00:00Z", True),
                ("still-running", "running", None, False),
            ]:
                run_dir = runs_root / run_id
                benchmark.write_json(
                    run_dir / "run.json",
                    {
                        "runId": run_id,
                        "status": status,
                        "completedAt": completed_at,
                    },
                )
                if evaluated:
                    benchmark.write_json(
                        run_dir / "evaluation" / "automated.json",
                        {"problems": [{"file": "problem-01.sgf"}]},
                    )

            selected = benchmark.reviewable_run(runs_root=runs_root)

        self.assertEqual(selected.name, "newest")

    def test_review_parser_does_not_require_a_run_id(self):
        args = benchmark.build_parser().parse_args(["review", "--no-open"])

        self.assertIsNone(args.run_id)
        self.assertTrue(args.no_open)

    def test_completed_review_requires_difficulty_only_for_valid_problems(self):
        files = [f"problem-{index:02d}.sgf" for index in range(1, 6)]
        problems = [
            {
                "file": file,
                "status": "pending",
                "valid": None,
                "realistic": None,
                "estimatedDifficulty": None,
                "quality": None,
                "reviewedAt": None,
            }
            for file in files
        ]
        problems[0].update(
            {
                "status": "completed",
                "valid": False,
                "realistic": False,
                "estimatedDifficulty": "20-30 kyu",
                "quality": 1,
            }
        )
        normalized = benchmark.normalize_review(
            {
                "reviewId": "reviewer-one",
                "reviewerName": "First Reviewer",
                "problems": problems,
            },
            files,
            "2026-08-05T12:00:00Z",
        )

        self.assertIsNone(normalized["problems"][0]["estimatedDifficulty"])
        problems[0].update({"valid": True, "realistic": True, "estimatedDifficulty": None})
        with self.assertRaisesRegex(ValueError, "estimated difficulty"):
            benchmark.normalize_review(
                {
                    "reviewId": "reviewer-two",
                    "reviewerName": "Second Reviewer",
                    "problems": problems,
                },
                files,
            )

    def test_review_store_keeps_independent_reviewer_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            files = [f"problem-{index:02d}.sgf" for index in range(1, 6)]
            benchmark.write_json(
                run_dir / "evaluation" / "automated.json",
                {"problems": [{"file": file} for file in files]},
            )
            benchmark.write_json(
                run_dir / "evaluation" / "results.json",
                {"problems": [{"file": file} for file in files]},
            )

            def review(review_id, name):
                return {
                    "reviewId": review_id,
                    "reviewerName": name,
                    "problems": [
                        {
                            "file": file,
                            "status": "completed",
                            "valid": True,
                            "realistic": True,
                            "estimatedDifficulty": "10-19 kyu",
                            "quality": 4,
                            "reviewedAt": None,
                        }
                        for file in files
                    ],
                }

            benchmark.save_review(run_dir, "test-run", review("review-one", "Reviewer One"))
            store, _ = benchmark.save_review(
                run_dir,
                "test-run",
                review("review-two", "Reviewer Two"),
            )
            results = benchmark.read_json(run_dir / "evaluation" / "results.json")

        self.assertEqual(len(store["reviews"]), 2)
        self.assertEqual(results["humanReviews"]["reviewCount"], 2)
        self.assertEqual(len(results["problems"][0]["reviews"]), 2)


if __name__ == "__main__":
    unittest.main()
