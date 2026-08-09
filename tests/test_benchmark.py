import json
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import benchmark


class BenchmarkRunnerTests(unittest.TestCase):
    def test_run_defaults_to_ten_problems(self):
        args = benchmark.build_parser().parse_args(["run", "--model", "gpt-test"])

        self.assertEqual(args.harness, "codex")
        self.assertEqual(args.count, 10)
        self.assertEqual(args.timeout, 12 * 60 * 60)
        self.assertEqual(args.max_attempts, 5)
        self.assertEqual(args.retry_base_delay, 15)
        self.assertEqual(args.retry_max_delay, 120)
        self.assertEqual(benchmark.DEFAULT_CLAUDE_MAX_ROUNDS, 20)
        self.assertEqual(benchmark.DEFAULT_CLAUDE_STALE_ROUND_LIMIT, 3)
        self.assertEqual(benchmark.DEFAULT_CLAUDE_SESSION_RESET_GRACE_SECONDS, 60)
        self.assertEqual(benchmark.CLAUDE_OUTPUT_TOKEN_MAX, 128_000)
        self.assertEqual(benchmark.DEFAULT_OPENCODE_MAX_ROUNDS, 20)
        self.assertEqual(benchmark.OPENCODE_OUTPUT_TOKEN_MAX, 65_536)
        self.assertIsNone(args.duplicate_query_limit)
        self.assertEqual(benchmark.duplicate_query_limit(args), 50)
        self.assertEqual(benchmark.retry_schedule(5, 15, 120), [15, 30, 60, 120])
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
        self.assertEqual(
            benchmark.DIFFICULTY_BANDS[-2:],
            ("2-3 dan", "4 dan or harder"),
        )

    def test_progress_message_reports_outputs_and_originality_queries(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "outputs").mkdir()
            (run_dir / "originality").mkdir()
            (run_dir / "outputs" / "problem-01.sgf").write_text(
                "(;SZ[19])", encoding="utf-8"
            )
            (run_dir / "outputs" / "problem-02.sgf").write_text(
                "(;SZ[19])", encoding="utf-8"
            )
            benchmark.write_json(
                run_dir / "originality" / "summary.json",
                {"queriesUsed": 8, "queryLimit": 50},
            )

            message = benchmark.benchmark_progress_message(
                run_dir,
                "Codex CLI",
                attempt_number=1,
                max_attempts=5,
                expected_count=10,
                elapsed_seconds=125,
            )

        self.assertEqual(
            message,
            "Still running Codex CLI (attempt 1/5): 2 minutes 5 seconds elapsed; "
            "2/10 SGFs written; 8/50 originality queries used.",
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
        environment = benchmark.harness_environment(args, Path("/tmp/run"))

        self.assertEqual(args.harness, "claude")
        self.assertEqual(args.reasoning_effort, "high")
        self.assertEqual(benchmark.harness_executable(args), "/opt/claude")
        self.assertEqual(command[0], "/opt/claude")
        self.assertIn("--safe-mode", command)
        self.assertIn("--print", command)
        self.assertEqual(command[command.index("--input-format") + 1], "stream-json")
        self.assertEqual(command[command.index("--output-format") + 1], "stream-json")
        self.assertIn("--no-session-persistence", command)
        self.assertIn("dontAsk", command)
        self.assertIn("Read,Write,Edit,Glob,Grep", command)
        self.assertIn("Bash,PowerShell,WebFetch,WebSearch,mcp__*", command)
        self.assertEqual(command[command.index("--model") + 1], "claude-sonnet-4-6")
        self.assertEqual(command[command.index("--effort") + 1], "high")
        self.assertEqual(environment["CLAUDE_CODE_MAX_OUTPUT_TOKENS"], "128000")
        self.assertNotIn("exec", command)

    def test_claude_streaming_session_continues_flexibly_after_output_boundary(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "claude",
                "--model",
                "claude-fable-5",
                "--local-only",
            ]
        )
        fake_cli = """import json
import os
from pathlib import Path
import sys

capture = Path("captured-inputs.jsonl")
for turn, line in enumerate(sys.stdin, 1):
    message = json.loads(line)
    with capture.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"message": message, "limit": os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")}) + "\\n")
    if turn == 1:
        for index in range(1, 5):
            Path("outputs", f"problem-{index:02d}.sgf").write_text("(;SZ[19])", encoding="utf-8")
        result = {
            "type": "result",
            "subtype": "success",
            "is_error": True,
            "session_id": "stream-session",
            "result": "Claude's response exceeded the 128000 output token maximum.",
        }
    else:
        for index in range(5, 11):
            Path("outputs", f"problem-{index:02d}.sgf").write_text("(;SZ[19])", encoding="utf-8")
        result = {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "session_id": "stream-session",
            "result": "Finished the benchmark.",
        }
    print(json.dumps(result), flush=True)
"""

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "outputs").mkdir()
            script = run_dir / "fake-claude.py"
            script.write_text(fake_cli, encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                result = benchmark.run_claude_streaming_session(
                    args,
                    [sys.executable, str(script)],
                    run_dir,
                    "Create the complete benchmark.",
                    "Claude CLI",
                    timeout_seconds=10,
                    attempt_number=1,
                )
            inputs = [
                json.loads(line)
                for line in (run_dir / "captured-inputs.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(result["roundStopReason"], "outputs_complete")
        self.assertEqual(len(result["rounds"]), 2)
        self.assertTrue(result["rounds"][0]["outputLimitBoundary"])
        self.assertEqual(result["rounds"][0]["outputFileCountAfter"], 4)
        self.assertEqual(result["rounds"][1]["outputFileCountAfter"], 10)
        self.assertEqual(len(inputs), 2)
        self.assertEqual(inputs[0]["limit"], "128000")
        self.assertEqual(
            inputs[0]["message"]["message"]["content"],
            "Create the complete benchmark.",
        )
        continuation = inputs[1]["message"]["message"]["content"]
        self.assertIn("same Claude session", continuation)
        self.assertIn("may research, construct, revise", continuation)
        self.assertIn("`problem-05.sgf`", continuation)
        self.assertIn("does not assign one problem per turn", continuation.lower())

    def test_claude_streaming_session_stops_after_three_stale_turns(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "claude",
                "--model",
                "claude-fable-5",
                "--local-only",
            ]
        )
        fake_cli = """import json
from pathlib import Path
import sys

capture = Path("captured-stale-inputs.jsonl")
for turn, line in enumerate(sys.stdin, 1):
    message = json.loads(line)
    with capture.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(message) + "\\n")
    print(json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "session_id": "stale-session",
        "result": f"Planning turn {turn}.",
    }), flush=True)
"""

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "outputs").mkdir()
            script = run_dir / "fake-stale-claude.py"
            script.write_text(fake_cli, encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                result = benchmark.run_claude_streaming_session(
                    args,
                    [sys.executable, str(script)],
                    run_dir,
                    "Create the complete benchmark.",
                    "Claude CLI",
                    timeout_seconds=10,
                    attempt_number=1,
                )
            inputs = [
                json.loads(line)
                for line in (run_dir / "captured-stale-inputs.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(result["roundStopReason"], "stale")
        self.assertEqual(len(result["rounds"]), 3)
        self.assertEqual(result["rounds"][-1]["consecutiveStaleRounds"], 3)
        self.assertEqual(len(inputs), 3)
        second_turn = inputs[1]["message"]["content"]
        final_turn = inputs[2]["message"]["content"]
        self.assertNotIn("FINAL NO-PROGRESS TURN", second_turn)
        self.assertIn("FINAL NO-PROGRESS TURN", final_turn)
        self.assertIn("2 consecutive continuation turns", final_turn)
        self.assertIn("3-turn no-progress limit", final_turn)

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
        self.assertEqual(command[command.index("--sandbox") + 1], "workspace")
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
        self.assertEqual(
            environment["OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX"],
            "65536",
        )
        self.assertEqual(config["permission"]["*"], "deny")
        self.assertEqual(config["permission"]["edit"], "allow")
        self.assertNotIn("bash", [key for key, value in config["permission"].items() if value == "allow"])

    def test_claude_version_preflight_requires_streaming_release(self):
        self.assertIsNone(benchmark.claude_version_error("2.1.217 (Claude Code)"))
        self.assertIsNone(benchmark.claude_version_error("Claude Code v3.0.0"))
        self.assertIn("2.1.217 or newer", benchmark.claude_version_error("2.1.216") or "")
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

    def test_opencode_model_catalog_parser_handles_ansi_and_bullets(self):
        completed = subprocess.CompletedProcess(
            [],
            0,
            stdout=(
                "\x1b[32mopenai/gpt-5.2\x1b[0m\n"
                "- openrouter/deepseek/deepseek-v4-flash-0731\n"
                "not a model identifier\n"
            ),
            stderr="",
        )
        with mock.patch.object(benchmark.subprocess, "run", return_value=completed) as process:
            models = benchmark.opencode_available_models("/opt/opencode")

        self.assertEqual(
            models,
            [
                "openai/gpt-5.2",
                "openrouter/deepseek/deepseek-v4-flash-0731",
            ],
        )
        self.assertEqual(
            process.call_args.args[0],
            ["/opt/opencode", "--pure", "models"],
        )

    def test_opencode_model_validation_explains_extra_provider_prefix(self):
        available = [
            "opencode/deepseek-v4-flash",
            "opencode/deepseek-v4-flash-free",
            "openrouter/deepseek/deepseek-v4-flash-0731",
        ]
        with mock.patch.object(
            benchmark,
            "opencode_available_models",
            return_value=available,
        ):
            error = benchmark.opencode_model_validation_error(
                "/opt/opencode",
                "opencode/openrouter/deepseek/deepseek-v4-flash-0731",
            )

        self.assertIsNotNone(error)
        self.assertIn("parsed as provider 'opencode'", error or "")
        self.assertIn(
            "Did you mean: 'openrouter/deepseek/deepseek-v4-flash-0731'?",
            error or "",
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

    def test_claude_usage_accumulates_across_continuation_results(self):
        events = "\n".join(
            [
                json.dumps(
                    {
                        "type": "result",
                        "subtype": "success",
                        "is_error": True,
                        "session_id": "continued-session",
                        "result": "Response exceeded the 128000 output token maximum.",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                        "modelUsage": {
                            "claude-fable-5": {
                                "inputTokens": 10,
                                "outputTokens": 20,
                                "costUSD": 0.5,
                                "contextWindow": 1_000_000,
                                "maxOutputTokens": 128_000,
                            }
                        },
                        "total_cost_usd": 0.5,
                        "num_turns": 2,
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "subtype": "success",
                        "is_error": False,
                        "session_id": "continued-session",
                        "result": "Finished.",
                        "usage": {"input_tokens": 30, "output_tokens": 40},
                        "modelUsage": {
                            "claude-fable-5": {
                                "inputTokens": 30,
                                "outputTokens": 40,
                                "costUSD": 0.75,
                                "contextWindow": 1_000_000,
                                "maxOutputTokens": 128_000,
                            }
                        },
                        "total_cost_usd": 0.75,
                        "num_turns": 3,
                    }
                ),
            ]
        )

        parsed = benchmark.parse_claude_events(events)

        self.assertIsNone(parsed["failureMessage"])
        self.assertEqual(parsed["finalMessage"], "Finished.")
        self.assertEqual(parsed["usage"]["usage"]["input_tokens"], 40)
        self.assertEqual(parsed["usage"]["usage"]["output_tokens"], 60)
        self.assertEqual(parsed["usage"]["total_cost_usd"], 1.25)
        self.assertEqual(parsed["usage"]["num_turns"], 5)
        model_usage = parsed["usage"]["modelUsage"]["claude-fable-5"]
        self.assertEqual(model_usage["costUSD"], 1.25)
        self.assertEqual(model_usage["maxOutputTokens"], 128_000)

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
        streamed = {
            "stdout": stdout,
            "stderr": "",
            "input": "{}\n",
            "exitCode": 1,
            "processExitCode": 1,
            "timedOut": False,
            "timeoutMessage": None,
            "durationSeconds": 0.1,
            "rounds": [],
            "roundStopReason": "harness_failed",
        }

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="2.1.217"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(
                    benchmark,
                    "run_claude_streaming_session",
                    return_value=streamed,
                ),
                mock.patch.object(benchmark, "run_evaluator") as evaluator,
                mock.patch.object(benchmark, "build_run_index") as indexer,
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            self.assertEqual(exit_code, 2)
            self.assertFalse((runs_root / "claude-invalid-model").exists())
            evaluator.assert_not_called()
            indexer.assert_not_called()

    def test_codex_model_effort_rejection_discards_run_before_evaluation(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--model",
                "gpt-5.5",
                "--reasoning-effort",
                "max",
                "--run-id",
                "codex-invalid-model-effort",
                "--local-only",
            ]
        )
        message = (
            "Unsupported value: 'max' is not supported with the "
            "'gpt-5.5-codex-1p-codexswic-ev3' model. Supported values are: "
            "'none', 'low', 'medium', 'high', and 'xhigh'."
        )
        completed = subprocess.CompletedProcess(
            [],
            1,
            stdout=json.dumps({"type": "error", "message": message}),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="codex-cli 0.144.1"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", return_value=completed),
                mock.patch.object(benchmark, "run_evaluator") as evaluator,
                mock.patch.object(benchmark, "build_run_index") as indexer,
            ):
                console_error = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(console_error):
                    exit_code = benchmark.run_command(args)

            self.assertEqual(exit_code, 2)
            self.assertFalse((runs_root / "codex-invalid-model-effort").exists())
            self.assertIn("Benchmark configuration", console_error.getvalue())
            self.assertIn("Check --model and --reasoning-effort", console_error.getvalue())
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

    def test_opencode_model_preflight_rejects_unknown_id_before_creating_run(self):
        model = "opencode/openrouter/deepseek/deepseek-v4-flash-0731"
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "opencode",
                "--model",
                model,
                "--run-id",
                "opencode-invalid-model-preflight",
                "--local-only",
            ]
        )
        available = [
            "opencode/deepseek-v4-flash",
            "openrouter/deepseek/deepseek-v4-flash-0731",
        ]

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="1.18.15"),
                mock.patch.object(
                    benchmark,
                    "opencode_available_models",
                    return_value=available,
                ),
                mock.patch.object(benchmark, "run_evaluator") as evaluator,
                mock.patch.object(benchmark, "build_run_index") as indexer,
            ):
                console_error = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(console_error):
                    exit_code = benchmark.run_command(args)

            self.assertEqual(exit_code, 2)
            self.assertEqual(list(runs_root.iterdir()), [])
            self.assertIn("OpenCode does not list model", console_error.getvalue())
            self.assertIn(
                "Did you mean: 'openrouter/deepseek/deepseek-v4-flash-0731'?",
                console_error.getvalue(),
            )
            self.assertIn("No model was invoked", console_error.getvalue())
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
                mock.patch.object(
                    benchmark,
                    "opencode_model_validation_error",
                    return_value=None,
                ),
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
        streamed = {
            "stdout": stdout,
            "stderr": "",
            "input": "{}\n",
            "exitCode": 0,
            "processExitCode": 0,
            "timedOut": False,
            "timeoutMessage": None,
            "durationSeconds": 0.1,
            "rounds": [],
            "roundStopReason": "outputs_complete",
        }

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
                mock.patch.object(benchmark, "cli_version", return_value="2.1.217"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(
                    benchmark,
                    "run_claude_streaming_session",
                    return_value=streamed,
                ),
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
            self.assertEqual(manifest["harness"]["outputTokenCeiling"], 128_000)
            self.assertTrue(manifest["harness"]["roundPolicy"]["sameSession"])
            self.assertEqual(manifest["harness"]["roundPolicy"]["maxRounds"], 20)
            self.assertEqual(manifest["harness"]["roundPolicy"]["staleRoundLimit"], 3)
            self.assertEqual(manifest["harness"]["roundStopReason"], "outputs_complete")
            self.assertEqual(manifest["artifacts"]["stdout"], "logs/claude-events.jsonl")
            self.assertEqual(manifest["artifacts"]["harnessInput"], "logs/claude-input.jsonl")
            self.assertTrue((run_dir / "logs" / "claude-events.jsonl").exists())
            self.assertEqual(
                (run_dir / "logs" / "claude-input.jsonl").read_text(encoding="utf-8"),
                "{}\n",
            )
            self.assertEqual(final_message, "Created 10 problems.")
            self.assertIn("Reasoning effort: CLI/model default", console.getvalue())
            self.assertIn("Execution timeout: 12 hours (43,200 seconds)", console.getvalue())
            self.assertIn("Claude per-response output ceiling: 128,000 tokens", console.getvalue())
            self.assertIn("Progress updates every 1 minute", console.getvalue())
            self.assertIn("Model phase finished in", console.getvalue())
            self.assertIn("Evaluation finished in", console.getvalue())
            self.assertRegex(
                console.getvalue().strip().splitlines()[-1],
                r"^Benchmark finished in .+\.$",
            )

    def test_claude_session_limit_pauses_preserves_outputs_and_reuses_retry_slot(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "claude",
                "--model",
                "claude-fable-5",
                "--run-id",
                "claude-session-limit",
                "--max-attempts",
                "1",
                "--local-only",
            ]
        )
        limit_message = (
            "You've hit your session limit · resets 8:50pm "
            "(America/Los_Angeles)"
        )
        limited_stdout = json.dumps(
            {
                "type": "result",
                "subtype": "error_during_execution",
                "is_error": True,
                "session_id": "session-limited",
                "result": limit_message,
            }
        )
        success_stdout = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "session_id": "session-resumed",
                "result": "Created the remaining problems.",
            }
        )
        invocation_tasks: list[str] = []

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)

            def stream_session(
                _args,
                _command,
                run_dir,
                task,
                _label,
                _timeout_seconds,
                _attempt_number,
            ):
                invocation_tasks.append(task)
                if len(invocation_tasks) == 1:
                    for index in range(1, 5):
                        (run_dir / "outputs" / f"problem-{index:02d}.sgf").write_text(
                            "(;SZ[19])", encoding="utf-8"
                        )
                    return {
                        "stdout": limited_stdout,
                        "stderr": "",
                        "input": "limited input\n",
                        "exitCode": 1,
                        "processExitCode": 1,
                        "timedOut": False,
                        "timeoutMessage": None,
                        "failureMessage": limit_message,
                        "durationSeconds": 1.0,
                        "rounds": [],
                        "roundStopReason": "harness_failed",
                    }
                self.assertTrue((run_dir / "outputs" / "problem-01.sgf").exists())
                for index in range(5, 11):
                    (run_dir / "outputs" / f"problem-{index:02d}.sgf").write_text(
                        "(;SZ[19])", encoding="utf-8"
                    )
                return {
                    "stdout": success_stdout,
                    "stderr": "",
                    "input": "resumed input\n",
                    "exitCode": 0,
                    "processExitCode": 0,
                    "timedOut": False,
                    "timeoutMessage": None,
                    "failureMessage": None,
                    "durationSeconds": 1.0,
                    "rounds": [],
                    "roundStopReason": "outputs_complete",
                }

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

            resume_at = datetime(2026, 8, 9, 3, 51, tzinfo=timezone.utc)
            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="2.1.217"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(
                    benchmark,
                    "run_claude_streaming_session",
                    side_effect=stream_session,
                ),
                mock.patch.object(
                    benchmark,
                    "claude_session_limit_reset_at",
                    return_value=resume_at,
                ),
                mock.patch.object(
                    benchmark,
                    "claude_session_limit_pause_seconds",
                    return_value=60,
                ),
                mock.patch.object(
                    benchmark,
                    "wait_for_claude_session_reset",
                    return_value=60,
                ) as waiter,
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

            run_dir = runs_root / "claude-session-limit"
            manifest = benchmark.read_json(run_dir / "run.json")
            attempts = manifest["harness"]["attempts"]

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(invocation_tasks), 2)
        self.assertIn("Resume the Tsumego Bench run", invocation_tasks[1])
        self.assertIn("4/10 expected SGF files are present", invocation_tasks[1])
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["outcome"], "session_limit_pause")
        self.assertEqual(attempts[0]["sessionLimitPauseSeconds"], 60)
        self.assertNotIn("archivedOutputs", attempts[0])
        self.assertEqual(attempts[1]["outcome"], "success")
        self.assertEqual(manifest["harness"]["sessionLimitPauseCount"], 1)
        self.assertEqual(manifest["harness"]["sessionLimitPauseSeconds"], 60)
        self.assertFalse(
            manifest["harness"]["retryPolicy"]["sessionLimitConsumesAttempt"]
        )
        waiter.assert_called_once()
        self.assertIn("does not consume transient retry attempt 1/1", console.getvalue())
        self.assertIn("Resuming model attempt 1/1", console.getvalue())

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
        streamed = {
            "stdout": partial_stdout.decode("utf-8"),
            "stderr": (
                b"partial stderr: \xff\n".decode("utf-8", errors="replace")
                + "Claude CLI timed out after 1 second.\n"
            ),
            "input": "{}\n",
            "exitCode": 124,
            "processExitCode": -15,
            "timedOut": True,
            "timeoutMessage": "Claude CLI timed out after 1 second.",
            "durationSeconds": 1.0,
            "rounds": [],
            "roundStopReason": "timeout",
        }

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
                mock.patch.object(
                    benchmark,
                    "run_claude_streaming_session",
                    return_value=streamed,
                ),
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

    def test_grok_transient_failure_retries_and_preserves_attempt_artifacts(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "grok",
                "--model",
                "grok-4.5",
                "--run-id",
                "grok-retry-success",
                "--max-attempts",
                "3",
                "--retry-base-delay",
                "1",
                "--retry-max-delay",
                "2",
                "--local-only",
            ]
        )
        failure_message = (
            'Internal error: "reqwest error stream: error sending request for url '
            '(https://cli-chat-proxy.grok.com/v1/responses)"'
        )
        failed_stdout = json.dumps({"type": "error", "message": failure_message})
        successful_stdout = "\n".join(
            [
                json.dumps({"type": "text", "data": "Created 10 problems."}),
                json.dumps(
                    {
                        "type": "end",
                        "stopReason": "end_turn",
                        "sessionId": "grok-session-retried",
                    }
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            invocation_count = 0

            def invoke(*_arguments, **keywords):
                nonlocal invocation_count
                invocation_count += 1
                if invocation_count == 1:
                    output = Path(keywords["cwd"]) / "outputs" / "problem-01.sgf"
                    output.write_text("(;SZ[19])", encoding="utf-8")
                    return subprocess.CompletedProcess(
                        [], 1, stdout=failed_stdout, stderr="transport failed"
                    )
                return subprocess.CompletedProcess(
                    [], 0, stdout=successful_stdout, stderr=""
                )

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
                mock.patch.object(benchmark.subprocess, "run", side_effect=invoke) as process,
                mock.patch.object(benchmark.time, "sleep") as sleeper,
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

            run_dir = runs_root / "grok-retry-success"
            manifest = benchmark.read_json(run_dir / "run.json")
            attempts = manifest["harness"]["attempts"]

            self.assertEqual(exit_code, 0)
            self.assertEqual(process.call_count, 2)
            sleeper.assert_called_once_with(1)
            self.assertEqual(len(attempts), 2)
            self.assertEqual(attempts[0]["outcome"], "transient_failure")
            self.assertTrue(attempts[0]["retryable"])
            self.assertEqual(attempts[0]["retryDelaySeconds"], 1)
            self.assertEqual(attempts[0]["outputFileCount"], 1)
            self.assertEqual(attempts[1]["outcome"], "success")
            self.assertEqual(
                attempts[0]["archivedOutputs"],
                "logs/attempts/attempt-01/outputs",
            )
            self.assertTrue(
                (run_dir / attempts[0]["archivedOutputs"] / "problem-01.sgf").exists()
            )
            self.assertFalse((run_dir / "outputs" / "problem-01.sgf").exists())
            self.assertTrue((run_dir / attempts[0]["stdout"]).exists())
            self.assertTrue((run_dir / attempts[1]["stdout"]).exists())
            self.assertIn("Attempt 1/3 failed", console.getvalue())
            self.assertIn("Retrying in 1 second", console.getvalue())
            self.assertIn("succeeded on attempt 2/3", console.getvalue())

    def test_grok_exhausted_transient_retries_report_every_attempt(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "grok",
                "--model",
                "grok-4.5",
                "--run-id",
                "grok-retry-failed",
                "--max-attempts",
                "3",
                "--retry-base-delay",
                "1",
                "--retry-max-delay",
                "2",
                "--local-only",
            ]
        )
        failure_message = (
            'Internal error: "reqwest error stream: error sending request for url '
            '(https://cli-chat-proxy.grok.com/v1/responses)"'
        )
        failed = subprocess.CompletedProcess(
            [],
            1,
            stdout=json.dumps({"type": "error", "message": failure_message}),
            stderr="transport failed",
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
                mock.patch.object(benchmark, "cli_version", return_value="grok 0.2.121"),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", return_value=failed) as process,
                mock.patch.object(benchmark.time, "sleep") as sleeper,
                mock.patch.object(benchmark, "run_evaluator", side_effect=evaluate),
                mock.patch.object(
                    benchmark,
                    "build_run_index",
                    return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
                ),
            ):
                console_error = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(console_error):
                    exit_code = benchmark.run_command(args)

            run_dir = runs_root / "grok-retry-failed"
            manifest = benchmark.read_json(run_dir / "run.json")
            attempts = manifest["harness"]["attempts"]
            report = console_error.getvalue()

            self.assertEqual(exit_code, 1)
            self.assertEqual(process.call_count, 3)
            self.assertEqual(sleeper.call_args_list, [mock.call(1), mock.call(2)])
            self.assertEqual(len(attempts), 3)
            self.assertTrue(all(attempt["retryable"] for attempt in attempts))
            self.assertTrue(
                all(attempt["outcome"] == "transient_failure" for attempt in attempts)
            )
            self.assertIn("after 3 attempts", report)
            self.assertIn("exponential backoff waited 3 seconds total", report)
            self.assertIn("Attempt details:", report)
            self.assertIn("1. transient failure", report)
            self.assertIn("3. transient failure", report)
            self.assertIn("reqwest error stream", report)

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

            invocation_count = 0

            def invoke(*_arguments, **keywords):
                nonlocal invocation_count
                invocation_count += 1
                output_dir = Path(keywords["cwd"]) / "outputs"
                last_problem = 4 if invocation_count == 1 else 10
                first_problem = 1 if invocation_count == 1 else 5
                for index in range(first_problem, last_problem + 1):
                    (output_dir / f"problem-{index:02d}.sgf").write_text(
                        "(;SZ[19])",
                        encoding="utf-8",
                    )
                return completed

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
                mock.patch.object(
                    benchmark,
                    "opencode_model_validation_error",
                    return_value=None,
                ),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", side_effect=invoke) as process,
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
            self.assertEqual(manifest["harness"]["roundsCompleted"], 2)
            self.assertEqual(manifest["harness"]["roundStopReason"], "outputs_complete")
            self.assertEqual(manifest["harness"]["outputTokenCeiling"], 65_536)
            self.assertEqual(manifest["harness"]["roundPolicy"]["maxRounds"], 20)
            self.assertEqual(process.call_count, 2)
            self.assertEqual(
                [attempt["roundNumber"] for attempt in manifest["harness"]["attempts"]],
                [1, 2],
            )
            self.assertEqual(manifest["artifacts"]["stdout"], "logs/opencode-events.jsonl")
            self.assertIn(
                "inputs/opencode-config/opencode.json",
                [record["path"] for record in manifest["benchmark"]["inputFiles"]],
            )
            self.assertEqual(
                (run_dir / "logs" / "final-message.txt").read_text(encoding="utf-8"),
                "Created 10 problems.",
            )
            first_prompt = process.call_args_list[0].kwargs["input"]
            continuation_prompt = process.call_args_list[1].kwargs["input"]
            self.assertIn("Read `inputs/model-prompt.md`", first_prompt)
            self.assertIn("OpenCode generation round 2 of at most 20", continuation_prompt)
            self.assertIn("`outputs/problem-05.sgf`", continuation_prompt)
            self.assertNotIn("`outputs/problem-04.sgf`", continuation_prompt)
            environment = process.call_args_list[0].kwargs["env"]
            self.assertEqual(environment["OPENCODE_DISABLE_AUTOUPDATE"], "true")
            self.assertEqual(
                environment["OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX"],
                "65536",
            )
            self.assertTrue(
                (run_dir / "inputs" / "opencode-config" / "opencode.json").exists()
            )

    def test_opencode_stops_after_twenty_rounds_when_outputs_remain_missing(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "opencode",
                "--model",
                "openrouter/test-model",
                "--run-id",
                "opencode-round-cap",
                "--local-only",
            ]
        )
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "text",
                        "sessionID": "ses_round_cap",
                        "part": {
                            "messageID": "msg_round_cap",
                            "type": "text",
                            "text": "Continuing.",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "step_finish",
                        "sessionID": "ses_round_cap",
                        "part": {
                            "messageID": "msg_round_cap",
                            "reason": "length",
                            "tokens": {"input": 1, "output": 1},
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
                            "structuralPassed": 0,
                            "automatedGatePassed": 0,
                        }
                    },
                )
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")

            with (
                mock.patch.object(benchmark, "RUNS_ROOT", runs_root),
                mock.patch.object(benchmark, "cli_version", return_value="1.18.15"),
                mock.patch.object(
                    benchmark,
                    "opencode_model_validation_error",
                    return_value=None,
                ),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(
                    benchmark.subprocess,
                    "run",
                    return_value=completed,
                ) as process,
                mock.patch.object(benchmark, "run_evaluator", side_effect=evaluate),
                mock.patch.object(
                    benchmark,
                    "build_run_index",
                    return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
                ),
            ):
                console_error = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(console_error):
                    exit_code = benchmark.run_command(args)

            manifest = benchmark.read_json(runs_root / "opencode-round-cap" / "run.json")

            self.assertEqual(exit_code, 0)
            self.assertEqual(process.call_count, 20)
            self.assertEqual(manifest["harness"]["roundsCompleted"], 20)
            self.assertEqual(manifest["harness"]["roundStopReason"], "max_rounds")
            self.assertEqual(len(manifest["harness"]["attempts"]), 20)
            self.assertEqual(manifest["harness"]["usage"]["steps"], 20)
            self.assertIn("20-round cap", console_error.getvalue())

    def test_opencode_transient_retry_preserves_progress_inside_one_round(self):
        args = benchmark.build_parser().parse_args(
            [
                "run",
                "--harness",
                "opencode",
                "--model",
                "openrouter/test-model",
                "--run-id",
                "opencode-round-retry",
                "--max-attempts",
                "2",
                "--retry-base-delay",
                "1",
                "--retry-max-delay",
                "1",
                "--local-only",
            ]
        )
        failed = subprocess.CompletedProcess(
            [],
            1,
            stdout=json.dumps(
                {
                    "type": "error",
                    "sessionID": "ses_retry_failed",
                    "error": {"data": {"message": "Service unavailable"}},
                }
            ),
            stderr="",
        )
        succeeded = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps(
                {
                    "type": "step_finish",
                    "sessionID": "ses_retry_success",
                    "part": {
                        "messageID": "msg_retry_success",
                        "reason": "stop",
                        "tokens": {"input": 1, "output": 1},
                    },
                }
            ),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temporary:
            runs_root = Path(temporary)
            invocation_count = 0

            def invoke(*_arguments, **keywords):
                nonlocal invocation_count
                invocation_count += 1
                output_dir = Path(keywords["cwd"]) / "outputs"
                if invocation_count == 1:
                    (output_dir / "problem-01.sgf").write_text(
                        "(;SZ[19])",
                        encoding="utf-8",
                    )
                    return failed
                for index in range(2, 11):
                    (output_dir / f"problem-{index:02d}.sgf").write_text(
                        "(;SZ[19])",
                        encoding="utf-8",
                    )
                return succeeded

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
                mock.patch.object(benchmark, "cli_version", return_value="1.18.15"),
                mock.patch.object(
                    benchmark,
                    "opencode_model_validation_error",
                    return_value=None,
                ),
                mock.patch.object(benchmark, "git_commit", return_value="test-commit"),
                mock.patch.object(benchmark.subprocess, "run", side_effect=invoke),
                mock.patch.object(benchmark.time, "sleep") as sleeper,
                mock.patch.object(benchmark, "run_evaluator", side_effect=evaluate),
                mock.patch.object(
                    benchmark,
                    "build_run_index",
                    return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
                ),
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = benchmark.run_command(args)

            run_dir = runs_root / "opencode-round-retry"
            manifest = benchmark.read_json(run_dir / "run.json")
            attempts = manifest["harness"]["attempts"]

            self.assertEqual(exit_code, 0)
            sleeper.assert_called_once_with(1)
            self.assertEqual(manifest["harness"]["roundsCompleted"], 1)
            self.assertEqual(manifest["harness"]["roundStopReason"], "outputs_complete")
            self.assertEqual([attempt["roundNumber"] for attempt in attempts], [1, 1])
            self.assertEqual([attempt["attemptInRound"] for attempt in attempts], [1, 2])
            self.assertNotIn("archivedOutputs", attempts[0])
            self.assertTrue((run_dir / "outputs" / "problem-01.sgf").exists())

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
            model_prompt = (run_dir / "inputs" / "model-prompt.md").read_text(
                encoding="utf-8"
            )
            tool_guide = (run_dir / "inputs" / "originality-tool.md").read_text(
                encoding="utf-8"
            )
            summary_schema_exists = (
                run_dir / "inputs" / "originality-summary.schema.json"
            ).exists()

        self.assertIn("Create exactly 10 final candidate SGF files", task)
        self.assertIn("`outputs/problem-01.sgf`", task)
        self.assertIn("`outputs/problem-10.sgf`", task)
        self.assertNotIn("problem-11.sgf", task)
        self.assertEqual(task.count("target difficulty:"), 10)
        self.assertIn("at most two valid 20-30 kyu problems", task)
        self.assertIn("every valid problem rated 5-9 kyu or harder", task)
        self.assertIn("Problems harder than 1 dan are allowed", task)
        self.assertIn("roughly 50,000 existing problems", model_prompt)
        self.assertIn("Treat the easy slots as originality-intensive", model_prompt)
        self.assertIn("originality query budget is 50 requests", task)
        self.assertIn("without at least one `C[RIGHT]` endpoint", task)
        self.assertIn("query every exact final output again", task)
        self.assertIn("`queryNumber` and `queriesRemaining`", tool_guide)
        self.assertTrue(summary_schema_exists)

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

    def test_recognizes_model_effort_configuration_errors(self):
        message = (
            "Unsupported value: 'max' is not supported with the 'gpt-5.5' model. "
            "Supported values are: 'none', 'low', 'medium', 'high', and 'xhigh'."
        )

        self.assertTrue(benchmark.is_run_configuration_failure(message))
        self.assertTrue(
            benchmark.is_run_configuration_failure(
                "Invalid model_reasoning_effort for the selected model."
            )
        )
        self.assertFalse(
            benchmark.is_run_configuration_failure("The request timed out.")
        )

    def test_recognizes_retryable_transport_and_service_errors(self):
        self.assertTrue(
            benchmark.is_transient_harness_failure(
                'Internal error: "reqwest error stream: error sending request for url '
                '(https://cli-chat-proxy.grok.com/v1/responses)"'
            )
        )
        self.assertTrue(
            benchmark.is_transient_harness_failure(
                "Request failed with HTTP status 429: too many requests"
            )
        )
        self.assertFalse(
            benchmark.is_transient_harness_failure("Model not found: made-up-model")
        )
        self.assertFalse(
            benchmark.is_transient_harness_failure("Authentication failed: invalid API key")
        )

    def test_parses_claude_session_limit_reset_in_reported_timezone(self):
        message = (
            "You've hit your session limit · resets 8:50pm "
            "(America/Los_Angeles)"
        )
        now = datetime(2026, 8, 9, 2, 0, tzinfo=timezone.utc)

        reset_at = benchmark.claude_session_limit_reset_at(message, now=now)

        self.assertIsNotNone(reset_at)
        assert reset_at is not None
        self.assertEqual((reset_at.year, reset_at.month, reset_at.day), (2026, 8, 8))
        self.assertEqual((reset_at.hour, reset_at.minute), (20, 51))
        self.assertEqual(reset_at.utcoffset().total_seconds(), -7 * 60 * 60)
        self.assertEqual(
            benchmark.claude_session_limit_pause_seconds(reset_at, now=now),
            6_660,
        )
        self.assertTrue(benchmark.is_claude_session_limit_failure(message))
        self.assertTrue(benchmark.is_transient_harness_failure(message))

    def test_claude_session_limit_reset_rolls_to_next_day_when_needed(self):
        message = (
            "You've hit your session limit · resets 8:50pm "
            "(America/Los_Angeles)"
        )
        now = datetime(2026, 8, 9, 5, 0, tzinfo=timezone.utc)

        reset_at = benchmark.claude_session_limit_reset_at(message, now=now)

        self.assertIsNotNone(reset_at)
        assert reset_at is not None
        self.assertEqual((reset_at.year, reset_at.month, reset_at.day), (2026, 8, 9))
        self.assertEqual((reset_at.hour, reset_at.minute), (20, 51))

    def test_claude_session_limit_wait_returns_immediately_after_reset(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "outputs").mkdir()
            resume_at = datetime.now(timezone.utc)
            with mock.patch.object(benchmark.time, "sleep") as sleep:
                waited = benchmark.wait_for_claude_session_reset(
                    run_dir,
                    expected_count=10,
                    resume_at=resume_at,
                )

        self.assertEqual(waited, 0)
        sleep.assert_not_called()

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

    def test_review_site_readiness_tolerates_a_slow_first_response(self):
        process = mock.Mock()
        process.poll.return_value = None
        response = mock.MagicMock()
        response.__enter__.return_value.status = 200

        with (
            mock.patch(
                "benchmark.urllib.request.urlopen",
                side_effect=[TimeoutError("cold compile"), response],
            ) as urlopen,
            mock.patch("benchmark.time.sleep"),
        ):
            ready = benchmark.wait_for_review_site(
                "http://127.0.0.1:3001",
                process,
                timeout=30,
            )

        self.assertTrue(ready)
        self.assertEqual(urlopen.call_count, 2)
        self.assertGreater(urlopen.call_args.kwargs["timeout"], 1)

    def test_review_site_readiness_uses_windows_network_for_windows_node_under_wsl(self):
        process = mock.Mock()
        process.poll.return_value = None
        completed = subprocess.CompletedProcess(["curl.exe"], 0, "200", "")

        with (
            mock.patch(
                "benchmark.shutil.which",
                return_value="/mnt/c/Windows/System32/curl.exe",
            ),
            mock.patch("benchmark.subprocess.run", return_value=completed) as run,
            mock.patch("benchmark.urllib.request.urlopen") as urlopen,
        ):
            ready = benchmark.wait_for_review_site(
                "http://127.0.0.1:3001",
                process,
                timeout=30,
                windows_runtime=True,
            )

        self.assertTrue(ready)
        urlopen.assert_not_called()
        command = run.call_args.args[0]
        self.assertEqual(command[0], "/mnt/c/Windows/System32/curl.exe")
        self.assertIn("NUL", command)

    def test_review_terminal_state_is_restored_after_vite_changes_it(self):
        stdin = mock.Mock()
        stdin.isatty.return_value = True
        stdin.fileno.return_value = 7
        termios = mock.Mock()
        termios.TCSANOW = 0
        termios.tcgetattr.return_value = ["original settings"]

        with (
            mock.patch("benchmark.os.name", "posix"),
            mock.patch("benchmark.sys.stdin", stdin),
            mock.patch.dict("sys.modules", {"termios": termios}),
        ):
            state = benchmark.capture_terminal_state()
            benchmark.restore_terminal_state(state)

        self.assertEqual(state, (7, ["original settings"]))
        termios.tcsetattr.assert_called_once_with(7, 0, ["original settings"])

    def test_review_site_cannot_take_over_terminal_input(self):
        process = mock.Mock()

        with mock.patch("benchmark.subprocess.Popen", return_value=process) as popen:
            launched = benchmark.launch_review_site(["node", "dev-server.js"])

        self.assertIs(launched, process)
        popen.assert_called_once_with(
            ["node", "dev-server.js"],
            cwd=benchmark.PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
        )

    def test_review_url_uses_windows_url_handler_without_parsing_query_string(self):
        url = "http://127.0.0.1:3001/runs?review=1&run=example&token=secret"
        completed = subprocess.CompletedProcess(["rundll32.exe"], 0, "", "")

        def executable(name):
            return (
                "/mnt/c/Windows/System32/rundll32.exe"
                if name == "rundll32.exe"
                else None
            )

        with (
            mock.patch("benchmark.os.name", "posix"),
            mock.patch("benchmark.is_wsl", return_value=True),
            mock.patch("benchmark.shutil.which", side_effect=executable),
            mock.patch("benchmark.subprocess.run", return_value=completed) as run,
        ):
            opened = benchmark.open_review_url(url)

        self.assertTrue(opened)
        self.assertEqual(
            run.call_args.args[0],
            [
                "/mnt/c/Windows/System32/rundll32.exe",
                "url.dll,FileProtocolHandler",
                url,
            ],
        )

    def test_only_fully_passing_review_requires_human_difficulty_to_complete(self):
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
                "estimatedDifficulty": "5-9 kyu",
                "quality": 5,
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
        problems[0].update(
            {
                "valid": True,
                "realistic": False,
                "duplicate": False,
                "wellPathed": True,
                "estimatedDifficulty": None,
            }
        )
        unrealistic = benchmark.normalize_review(
            {
                "reviewId": "reviewer-two",
                "reviewerName": "Second Reviewer",
                "problems": problems,
            },
            files,
        )

        self.assertEqual(unrealistic["problems"][0]["status"], "completed")
        self.assertIsNone(unrealistic["problems"][0]["estimatedDifficulty"])
        self.assertIsNone(unrealistic["problems"][0]["quality"])
        problems[0].update({"realistic": True, "duplicate": True})
        duplicate = benchmark.normalize_review(
            {
                "reviewId": "reviewer-three",
                "reviewerName": "Third Reviewer",
                "problems": problems,
            },
            files,
        )

        self.assertEqual(duplicate["problems"][0]["status"], "completed")
        problems[0].update({"duplicate": False, "wellPathed": False})
        poorly_pathed = benchmark.normalize_review(
            {
                "reviewId": "reviewer-four",
                "reviewerName": "Fourth Reviewer",
                "problems": problems,
            },
            files,
        )

        self.assertEqual(poorly_pathed["problems"][0]["status"], "completed")
        problems[0].update({"wellPathed": True, "quality": None})
        valid_without_optional_fields = benchmark.normalize_review(
            {
                "reviewId": "reviewer-five",
                "reviewerName": "Fifth Reviewer",
                "problems": problems,
            },
            files,
        )

        self.assertEqual(valid_without_optional_fields["problems"][0]["status"], "pending")
        self.assertTrue(valid_without_optional_fields["problems"][0]["valid"])
        self.assertTrue(valid_without_optional_fields["problems"][0]["realistic"])
        self.assertIsNone(valid_without_optional_fields["problems"][0]["quality"])
        problems[0]["estimatedDifficulty"] = "4 dan or harder"
        valid_with_difficulty = benchmark.normalize_review(
            {
                "reviewId": "reviewer-six",
                "reviewerName": "Sixth Reviewer",
                "problems": problems,
            },
            files,
        )

        self.assertEqual(valid_with_difficulty["problems"][0]["status"], "completed")
        self.assertEqual(
            valid_with_difficulty["problems"][0]["estimatedDifficulty"],
            "4 dan or harder",
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
