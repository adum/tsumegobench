import json
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import benchmark


class BenchmarkRunnerTests(unittest.TestCase):
    def test_run_defaults_to_ten_problems(self):
        args = benchmark.build_parser().parse_args(["run", "--model", "gpt-test"])

        self.assertEqual(args.harness, "codex")
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

    def test_claude_harness_parser_and_command_are_non_interactive_and_restricted(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "claude",
                "--model",
                "claude-sonnet-4-6",
                "--effort",
                "high",
                "--claude",
                "/opt/claude",
            ]
        )

        command = benchmark.build_harness_command(args, Path("/tmp/run"), "/opt/claude")

        self.assertEqual(args.harness, "claude")
        self.assertEqual(args.reasoning_effort, "high")
        self.assertEqual(benchmark.harness_executable(args), "/opt/claude")
        self.assertEqual(command[0], "/opt/claude")
        self.assertIn("--safe-mode", command)
        self.assertIn("--print", command)
        self.assertIn("stream-json", command)
        self.assertIn("--no-session-persistence", command)
        self.assertIn("dontAsk", command)
        self.assertIn("Read,Write,Edit,Glob,Grep", command)
        self.assertIn("Bash,PowerShell,WebFetch,WebSearch,mcp__*", command)
        self.assertEqual(command[command.index("--model") + 1], "claude-sonnet-4-6")
        self.assertEqual(command[command.index("--effort") + 1], "high")
        self.assertNotIn("exec", command)

    def test_claude_version_preflight_requires_safe_mode_release(self):
        self.assertIsNone(benchmark.claude_version_error("2.1.169 (Claude Code)"))
        self.assertIsNone(benchmark.claude_version_error("Claude Code v3.0.0"))
        self.assertIn("2.1.169 or newer", benchmark.claude_version_error("0.2.40") or "")
        self.assertIn("Could not determine", benchmark.claude_version_error("development") or "")

    def test_cli_version_rejects_a_broken_executable(self):
        with mock.patch.object(
            benchmark.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 1, stdout="", stderr="syntax error"),
        ):
            self.assertIsNone(benchmark.cli_version("claude"))

    def test_claude_run_id_records_provider_and_harness(self):
        run_id = benchmark.unique_run_id("claude-sonnet-4-6", None, "claude")

        self.assertRegex(
            run_id,
            r"^\d{4}-\d{2}-\d{2}T\d{6}Z-anthropic-claude-sonnet-4-6-claude$",
        )

    def test_extracts_claude_session_result_and_usage(self):
        events = "\n".join(
            [
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "session_id": "session-1",
                        "model": "claude-sonnet-4-6",
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "subtype": "success",
                        "is_error": False,
                        "session_id": "session-1",
                        "result": "Created 10 problems.",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                        "modelUsage": {"claude-sonnet-4-6": {"costUSD": 0.12}},
                        "total_cost_usd": 0.12,
                        "duration_api_ms": 1234,
                        "num_turns": 4,
                    }
                ),
            ]
        )

        parsed = benchmark.parse_claude_events(events)

        self.assertEqual(parsed["threadId"], "session-1")
        self.assertEqual(parsed["finalMessage"], "Created 10 problems.")
        self.assertEqual(parsed["usage"]["usage"]["output_tokens"], 20)
        self.assertEqual(parsed["usage"]["total_cost_usd"], 0.12)
        self.assertEqual(parsed["usage"]["num_turns"], 4)
        self.assertEqual(parsed["eventCount"], 2)
        self.assertEqual(parsed["unparsedLineCount"], 0)
        self.assertIsNone(parsed["failureMessage"])

    def test_claude_model_rejection_discards_run_before_evaluation(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "claude",
                "--model",
                "made-up-model",
                "--run-id",
                "claude-invalid-model",
                "--local-only",
            ]
        )
        stdout = json.dumps(
            {
                "type": "result",
                "subtype": "error_during_execution",
                "is_error": True,
                "session_id": "session-2",
                "result": "Invalid model name: made-up-model",
            }
        )
        completed = subprocess.CompletedProcess([], 1, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="2.1.169"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", return_value=completed),
                mock.patch.object(benchmark, "run_evaluator") as evaluator,
                mock.patch.object(benchmark, "build_run_index") as indexer,
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            self.assertEqual(exit_code, 2)
            self.assertFalse((runs_root / "claude-invalid-model").exists())
            evaluator.assert_not_called()
            indexer.assert_not_called()

    def test_successful_claude_run_records_normalized_artifacts(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "claude",
                "--model",
                "claude-sonnet-4-6",
                "--run-id",
                "claude-success",
                "--local-only",
            ]
        )
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "session_id": "session-success",
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "subtype": "success",
                        "is_error": False,
                        "session_id": "session-success",
                        "result": "Created 10 problems.",
                        "usage": {"input_tokens": 100, "output_tokens": 200},
                    }
                ),
            ]
        )
        completed = subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)

            def evaluate(run_dir, _local_only):
                benchmark.write_json(
                    run_dir / "evaluation" / "automated.json",
                    {
                        "summary": {
                            "expectedProblems": 10,
                            "structuralPassed": 10,
                            "automatedGatePassed": 10,
                        }
                    },
                )
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")

            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="2.1.169"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", return_value=completed),
                mock.patch.object(benchmark, "run_evaluator", side_effect=evaluate),
                mock.patch.object(
                    benchmark,
                    "build_run_index",
                    return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
                ),
            ):
                console = io.StringIO()
                with redirect_stdout(console), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            run_dir = runs_root / "claude-success"
            manifest = benchmark.read_json(run_dir / "run.json")
            final_message = (run_dir / "logs" / "final-message.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["model"]["provider"], "anthropic")
            self.assertEqual(manifest["harness"]["name"], "claude-cli")
            self.assertEqual(manifest["harness"]["threadId"], "session-success")
            self.assertEqual(manifest["artifacts"]["stdout"], "logs/claude-events.jsonl")
            self.assertTrue((run_dir / "logs" / "claude-events.jsonl").exists())
            self.assertEqual(final_message, "Created 10 problems.")
            self.assertIn("Reasoning effort: CLI/model default", console.getvalue())

    def test_missing_claude_cli_creates_no_run(self):
        args = benchmark.build_parser().parse_args(
            ["run", "--harness", "claude", "--model", "claude-sonnet-4-6"]
        )

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value=None),
                mock.patch.object(benchmark, "run_evaluator") as evaluator,
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            self.assertEqual(exit_code, 2)
            self.assertEqual(list(runs_root.iterdir()), [])
            evaluator.assert_not_called()

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

    def test_review_fields_are_optional_after_any_review_activity(self):
        files = [f"problem-{index:02d}.sgf" for index in range(1, 6)]
        problems = [
            {
                "file": file,
                "status": "pending",
                "valid": None,
                "realistic": None,
                "duplicate": None,
                "wellPathed": None,
                "estimatedDifficulty": None,
                "quality": None,
                "reviewedAt": None,
            }
            for file in files
        ]
        problems[0].update(
            {
                "valid": False,
                "realistic": False,
                "duplicate": True,
                "wellPathed": True,
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
        self.assertTrue(normalized["problems"][0]["duplicate"])
        self.assertTrue(normalized["problems"][0]["wellPathed"])
        self.assertIsNone(normalized["problems"][0]["quality"])
        self.assertEqual(normalized["problems"][0]["status"], "completed")
        self.assertEqual(
            normalized["problems"][0]["reviewedAt"],
            "2026-08-05T12:00:00Z",
        )
        self.assertEqual(normalized["problems"][1]["status"], "pending")
        problems[0].update({"valid": True, "realistic": True, "estimatedDifficulty": None})
        valid_without_optional_fields = benchmark.normalize_review(
            {
                "reviewId": "reviewer-two",
                "reviewerName": "Second Reviewer",
                "problems": problems,
            },
            files,
        )

        self.assertEqual(valid_without_optional_fields["problems"][0]["status"], "completed")
        self.assertTrue(valid_without_optional_fields["problems"][0]["valid"])
        self.assertTrue(valid_without_optional_fields["problems"][0]["realistic"])
        self.assertIsNone(valid_without_optional_fields["problems"][0]["quality"])

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
                            "duplicate": False,
                            "wellPathed": True,
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
