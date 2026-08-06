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
        self.assertEqual(args.timeout, 12 * 60 * 60)
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

    def test_grok_harness_parser_and_command_are_non_interactive_and_restricted(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "grok",
                "--model",
                "grok-4.5",
                "--effort",
                "high",
                "--grok",
                "/opt/grok",
            ]
        )

        run_dir = Path("/tmp/run")
        command = benchmark.build_harness_command(args, run_dir, "/opt/grok")

        self.assertEqual(args.harness, "grok")
        self.assertEqual(args.reasoning_effort, "high")
        self.assertEqual(benchmark.harness_executable(args), "/opt/grok")
        self.assertEqual(command[0], "/opt/grok")
        self.assertIn("--no-auto-update", command)
        self.assertEqual(command[command.index("--cwd") + 1], str(run_dir))
        self.assertEqual(
            command[command.index("--prompt-file") + 1],
            str(run_dir / "inputs" / "task.md"),
        )
        self.assertEqual(command[command.index("--output-format") + 1], "streaming-json")
        self.assertEqual(command[command.index("--sandbox") + 1], "strict")
        self.assertIn("--always-approve", command)
        self.assertIn("--no-plan", command)
        self.assertIn("--no-subagents", command)
        self.assertIn("--no-memory", command)
        self.assertIn("--disable-web-search", command)
        self.assertIn("run_terminal_cmd,web_search,web_fetch,Agent", command)
        self.assertIn("MCPTool", command)
        self.assertEqual(command[command.index("--model") + 1], "grok-4.5")
        self.assertEqual(command[command.index("--effort") + 1], "high")

    def test_opencode_harness_parser_command_and_environment_are_restricted(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "opencode",
                "--model",
                "openai/gpt-5.2",
                "--effort",
                "high",
                "--opencode",
                "/opt/opencode",
            ]
        )

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            benchmark.copy_inputs(run_dir, benchmark.DEFAULT_PROBLEM_COUNT, "opencode")
            command = benchmark.build_harness_command(args, run_dir, "/opt/opencode")
            environment = benchmark.harness_environment(args, run_dir)

        self.assertEqual(args.harness, "opencode")
        self.assertEqual(args.reasoning_effort, "high")
        self.assertEqual(benchmark.harness_executable(args), "/opt/opencode")
        self.assertEqual(command[0], "/opt/opencode")
        self.assertEqual(command[1:3], ["--pure", "run"])
        self.assertEqual(command[command.index("--format") + 1], "json")
        self.assertEqual(command[command.index("--model") + 1], "openai/gpt-5.2")
        self.assertEqual(command[command.index("--agent") + 1], "build")
        self.assertEqual(command[command.index("--dir") + 1], str(run_dir))
        self.assertIn("--auto", command)
        self.assertEqual(command[command.index("--variant") + 1], "high")
        self.assertIsNotNone(environment)
        config = json.loads(environment["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(config["share"], "disabled")
        self.assertFalse(config["autoupdate"])
        self.assertFalse(config["formatter"])
        self.assertEqual(config["permission"]["*"], "deny")
        self.assertEqual(config["permission"]["edit"], "allow")
        self.assertNotIn("bash", [key for key, value in config["permission"].items() if value == "allow"])

    def test_claude_version_preflight_requires_safe_mode_release(self):
        self.assertIsNone(benchmark.claude_version_error("2.1.169 (Claude Code)"))
        self.assertIsNone(benchmark.claude_version_error("Claude Code v3.0.0"))
        self.assertIn("2.1.169 or newer", benchmark.claude_version_error("0.2.40") or "")
        self.assertIn("Could not determine", benchmark.claude_version_error("development") or "")

    def test_opencode_version_preflight_requires_isolated_permission_release(self):
        self.assertIsNone(benchmark.opencode_version_error("opencode 1.1.1"))
        self.assertIsNone(benchmark.opencode_version_error("1.2.0"))
        self.assertIn("1.1.1 or newer", benchmark.opencode_version_error("1.0.99") or "")
        self.assertIn("Could not determine", benchmark.opencode_version_error("development") or "")

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

    def test_grok_run_id_records_provider_and_harness(self):
        run_id = benchmark.unique_run_id("grok-4.5", None, "grok")

        self.assertRegex(
            run_id,
            r"^\d{4}-\d{2}-\d{2}T\d{6}Z-xai-grok-4-5-grok$",
        )

    def test_opencode_run_id_records_selected_provider_and_harness(self):
        run_id = benchmark.unique_run_id("openai/gpt-5.2", None, "opencode")

        self.assertRegex(
            run_id,
            r"^\d{4}-\d{2}-\d{2}T\d{6}Z-openai-gpt-5-2-opencode$",
        )

    def test_opencode_requires_provider_model_identifier(self):
        with self.assertRaisesRegex(ValueError, "provider/model"):
            benchmark.unique_run_id("gpt-5.2", None, "opencode")

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

    def test_extracts_grok_session_result_usage_and_text(self):
        events = "\n".join(
            [
                json.dumps({"type": "text", "data": "Reading the inputs."}),
                json.dumps({"type": "usage", "stopReason": "tool_use"}),
                json.dumps({"type": "text", "data": "Created "}),
                json.dumps({"type": "text", "data": "10 problems."}),
                json.dumps({"type": "usage", "stopReason": "end_turn"}),
                json.dumps(
                    {
                        "type": "end",
                        "stopReason": "end_turn",
                        "sessionId": "grok-session-1",
                        "requestId": "grok-request-1",
                        "usage": {"input_tokens": 30, "output_tokens": 40},
                        "modelUsage": {"grok-4.5": {"costUSD": 0.2}},
                        "total_cost_usd": 0.2,
                        "num_turns": 5,
                    }
                ),
            ]
        )

        parsed = benchmark.parse_grok_events(events)

        self.assertEqual(parsed["threadId"], "grok-session-1")
        self.assertEqual(parsed["finalMessage"], "Created 10 problems.")
        self.assertEqual(parsed["usage"]["usage"]["output_tokens"], 40)
        self.assertEqual(parsed["usage"]["total_cost_usd"], 0.2)
        self.assertEqual(parsed["usage"]["num_turns"], 5)
        self.assertEqual(parsed["eventCount"], 6)
        self.assertEqual(parsed["unparsedLineCount"], 0)
        self.assertIsNone(parsed["failureMessage"])

    def test_extracts_opencode_final_turn_session_usage_and_error(self):
        events = "\n".join(
            [
                json.dumps(
                    {
                        "type": "text",
                        "sessionID": "ses_opencode_1",
                        "part": {
                            "messageID": "msg_narration",
                            "type": "text",
                            "text": "Reading the packet.",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "step_finish",
                        "sessionID": "ses_opencode_1",
                        "part": {
                            "messageID": "msg_narration",
                            "reason": "tool-calls",
                            "cost": 0.01,
                            "tokens": {
                                "input": 100,
                                "output": 20,
                                "reasoning": 5,
                                "cache": {"read": 40, "write": 3},
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "text",
                        "sessionID": "ses_opencode_1",
                        "part": {
                            "messageID": "msg_final",
                            "type": "text",
                            "text": "Created 10 problems.",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "step_finish",
                        "sessionID": "ses_opencode_1",
                        "part": {
                            "messageID": "msg_final",
                            "reason": "stop",
                            "cost": 0.02,
                            "tokens": {"input": 50, "output": 10},
                        },
                    }
                ),
            ]
        )

        parsed = benchmark.parse_opencode_events(events)

        self.assertEqual(parsed["threadId"], "ses_opencode_1")
        self.assertEqual(parsed["finalMessage"], "Created 10 problems.")
        self.assertEqual(parsed["usage"]["input_tokens"], 150)
        self.assertEqual(parsed["usage"]["output_tokens"], 30)
        self.assertEqual(parsed["usage"]["reasoning_tokens"], 5)
        self.assertEqual(parsed["usage"]["cache_read_tokens"], 40)
        self.assertEqual(parsed["usage"]["cache_write_tokens"], 3)
        self.assertEqual(parsed["usage"]["cost_usd"], 0.03)
        self.assertEqual(parsed["usage"]["steps"], 2)
        self.assertEqual(parsed["eventCount"], 4)
        self.assertEqual(parsed["unparsedLineCount"], 0)
        self.assertIsNone(parsed["failureMessage"])

        error = benchmark.parse_opencode_events(
            json.dumps(
                {
                    "type": "error",
                    "sessionID": "ses_opencode_error",
                    "error": {
                        "name": "ProviderModelNotFoundError",
                        "data": {"message": "Model not found: openai/made-up-model"},
                    },
                }
            )
        )
        self.assertEqual(error["failureMessage"], "Model not found: openai/made-up-model")

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

    def test_grok_model_rejection_discards_run_before_evaluation(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "grok",
                "--model",
                "made-up-model",
                "--run-id",
                "grok-invalid-model",
                "--local-only",
            ]
        )
        stdout = json.dumps(
            {
                "type": "error",
                "message": "Model not found: made-up-model",
                "sessionId": "grok-session-2",
            }
        )
        completed = subprocess.CompletedProcess([], 1, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="grok 0.2.121"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", return_value=completed),
                mock.patch.object(benchmark, "run_evaluator") as evaluator,
                mock.patch.object(benchmark, "build_run_index") as indexer,
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            self.assertEqual(exit_code, 2)
            self.assertFalse((runs_root / "grok-invalid-model").exists())
            evaluator.assert_not_called()
            indexer.assert_not_called()

    def test_opencode_model_rejection_discards_run_before_evaluation(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "opencode",
                "--model",
                "openai/made-up-model",
                "--run-id",
                "opencode-invalid-model",
                "--local-only",
            ]
        )
        stdout = json.dumps(
            {
                "type": "error",
                "sessionID": "ses_opencode_2",
                "error": {
                    "name": "ProviderModelNotFoundError",
                    "data": {"message": "Model not found: openai/made-up-model"},
                },
            }
        )
        completed = subprocess.CompletedProcess([], 1, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="1.1.1"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", return_value=completed),
                mock.patch.object(benchmark, "run_evaluator") as evaluator,
                mock.patch.object(benchmark, "build_run_index") as indexer,
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            self.assertEqual(exit_code, 2)
            self.assertFalse((runs_root / "opencode-invalid-model").exists())
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
            self.assertIn("Execution timeout: 12 hours (43,200 seconds)", console.getvalue())

    def test_claude_timeout_decodes_partial_byte_logs_and_finishes_the_run(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "claude",
                "--model",
                "claude-opus-5",
                "--run-id",
                "claude-timeout",
                "--timeout",
                "1",
                "--local-only",
            ]
        )
        partial_stdout = (
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "session_id": "session-timeout",
                }
            )
            + "\n"
        ).encode("utf-8")
        timeout = subprocess.TimeoutExpired(
            ["claude"],
            1,
            output=partial_stdout,
            stderr=b"partial stderr: \xff\n",
        )

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)

            def evaluate(run_dir, _local_only):
                benchmark.write_json(
                    run_dir / "evaluation" / "automated.json",
                    {
                        "summary": {
                            "expectedProblems": 10,
                            "structuralPassed": 0,
                            "automatedGatePassed": 0,
                        }
                    },
                )
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")

            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="2.1.223"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", side_effect=timeout),
                mock.patch.object(benchmark, "run_evaluator", side_effect=evaluate) as evaluator,
                mock.patch.object(
                    benchmark,
                    "build_run_index",
                    return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
                ),
            ):
                console_error = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(console_error):
                    exit_code = benchmark.run_command(args)

            run_dir = runs_root / "claude-timeout"
            manifest = benchmark.read_json(run_dir / "run.json")
            stdout_log = (run_dir / "logs" / "claude-events.jsonl").read_text(
                encoding="utf-8"
            )
            stderr_log = (run_dir / "logs" / "claude-stderr.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(manifest["status"], "harness_failed")
            self.assertEqual(manifest["harness"]["exitCode"], 124)
            self.assertEqual(manifest["harness"]["threadId"], "session-timeout")
            self.assertEqual(
                manifest["harness"]["failureMessage"],
                "Claude CLI timed out after 1 second.",
            )
            self.assertIn("Harness timed out after 1 second.", manifest["condition"]["notes"])
            self.assertEqual(stdout_log, partial_stdout.decode("utf-8"))
            self.assertIn("partial stderr: �", stderr_log)
            self.assertIn("Claude CLI timed out after 1 second.", stderr_log)
            self.assertIn("Claude CLI timed out after 1 second.", console_error.getvalue())
            evaluator.assert_called_once_with(run_dir, True)

    def test_successful_grok_run_records_normalized_artifacts(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "grok",
                "--model",
                "grok-4.5",
                "--run-id",
                "grok-success",
                "--local-only",
            ]
        )
        stdout = "\n".join(
            [
                json.dumps({"type": "text", "data": "Created 10 problems."}),
                json.dumps(
                    {
                        "type": "end",
                        "stopReason": "end_turn",
                        "sessionId": "grok-session-success",
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
                mock.patch.object(benchmark, "cli_version", return_value="grok 0.2.121"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", return_value=completed) as process,
                mock.patch.object(benchmark, "run_evaluator", side_effect=evaluate),
                mock.patch.object(
                    benchmark,
                    "build_run_index",
                    return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
                ),
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            run_dir = runs_root / "grok-success"
            manifest = benchmark.read_json(run_dir / "run.json")

            self.assertEqual(exit_code, 0)
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["model"]["provider"], "xai")
            self.assertEqual(manifest["harness"]["name"], "grok-cli")
            self.assertEqual(manifest["harness"]["threadId"], "grok-session-success")
            self.assertEqual(manifest["artifacts"]["stdout"], "logs/grok-events.jsonl")
            self.assertEqual(
                (run_dir / "logs" / "final-message.txt").read_text(encoding="utf-8"),
                "Created 10 problems.",
            )
            self.assertIsNone(process.call_args.kwargs["input"])

    def test_successful_opencode_run_records_normalized_artifacts(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "opencode",
                "--model",
                "openai/gpt-5.2",
                "--run-id",
                "opencode-success",
                "--local-only",
            ]
        )
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "text",
                        "sessionID": "ses_opencode_success",
                        "part": {
                            "messageID": "msg_final",
                            "type": "text",
                            "text": "Created 10 problems.",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "step_finish",
                        "sessionID": "ses_opencode_success",
                        "part": {
                            "messageID": "msg_final",
                            "reason": "stop",
                            "cost": 0.1,
                            "tokens": {"input": 100, "output": 200},
                        },
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
                mock.patch.object(benchmark, "cli_version", return_value="1.1.1"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", return_value=completed) as process,
                mock.patch.object(benchmark, "run_evaluator", side_effect=evaluate),
                mock.patch.object(
                    benchmark,
                    "build_run_index",
                    return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
                ),
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            run_dir = runs_root / "opencode-success"
            manifest = benchmark.read_json(run_dir / "run.json")

            self.assertEqual(exit_code, 0)
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["model"]["provider"], "openai")
            self.assertEqual(manifest["harness"]["name"], "opencode-cli")
            self.assertEqual(manifest["harness"]["threadId"], "ses_opencode_success")
            self.assertEqual(manifest["artifacts"]["stdout"], "logs/opencode-events.jsonl")
            self.assertIn(
                "inputs/opencode-config/opencode.json",
                [record["path"] for record in manifest["benchmark"]["inputFiles"]],
            )
            self.assertEqual(
                (run_dir / "logs" / "final-message.txt").read_text(encoding="utf-8"),
                "Created 10 problems.",
            )
            self.assertIn("Read `inputs/model-prompt.md`", process.call_args.kwargs["input"])
            environment = process.call_args.kwargs["env"]
            self.assertEqual(environment["OPENCODE_DISABLE_AUTOUPDATE"], "true")
            self.assertTrue(
                (run_dir / "inputs" / "opencode-config" / "opencode.json").exists()
            )

    def test_missing_selected_cli_creates_no_run(self):
        for harness, model in (
            ("claude", "claude-sonnet-4-6"),
            ("grok", "grok-4.5"),
            ("opencode", "openai/gpt-5.2"),
        ):
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as temporary:
                args = benchmark.build_parser().parse_args(
                    ["run", "--harness", harness, "--model", model]
                )
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
