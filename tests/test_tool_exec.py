from __future__ import annotations

import pytest

from devflow_runner.errors import ToolExecutionError, ToolProtocolError, ToolReturnedError
from devflow_runner.loader import load_profile
from devflow_runner.models import Profile, ToolSpec
from devflow_runner.tool_exec import ToolExecutor


def tool_envelope(inputs: dict | None = None, *, tool: str = "fake.echo") -> dict:
    return {
        "meta": {
            "workflow": "test-workflow",
            "step": "test_step",
            "tool": tool,
            "dry_run": False,
        },
        "context": {
            "run_id": "test-run",
            "run_dir": "runs/test-run",
            "workflow": "test-workflow",
            "profile": "industrial",
            "dry_run": False,
        },
        "inputs": inputs or {},
    }


def profile_with_tool(name: str, script: str) -> Profile:
    return Profile(
        name="test-profile",
        tools={
            name: ToolSpec(
                command="python",
                args=[script],
                timeout_seconds=30,
            )
        },
    )


def test_tool_executor_parses_json_stdout(temp_project):
    profile = load_profile(temp_project, "industrial")
    executor = ToolExecutor(project_root=temp_project, profile=profile)

    result = executor.execute(
        tool_name="fake.echo",
        envelope=tool_envelope({"hello": "world"}),
    )

    assert result.ok is True
    assert result.data == {"hello": "world"}
    assert result.metrics["input_keys"] == 1


def test_tool_executor_rejects_invalid_input_envelope(temp_project):
    profile = load_profile(temp_project, "industrial")
    executor = ToolExecutor(project_root=temp_project, profile=profile)

    with pytest.raises(ToolProtocolError):
        executor.execute(tool_name="fake.echo", envelope={"meta": {}, "context": {}, "inputs": {}})


def test_tool_executor_rejects_invalid_json_stdout(temp_project):
    profile = profile_with_tool("fake.bad", "tools/fake/bad_stdout.py")
    executor = ToolExecutor(project_root=temp_project, profile=profile)

    with pytest.raises(ToolProtocolError):
        executor.execute(tool_name="fake.bad", envelope=tool_envelope(tool="fake.bad"))


def test_tool_executor_rejects_schema_invalid_stdout(temp_project):
    profile = profile_with_tool("fake.schema_invalid", "tools/fake/schema_invalid_stdout.py")
    executor = ToolExecutor(project_root=temp_project, profile=profile)

    with pytest.raises(ToolProtocolError):
        executor.execute(tool_name="fake.schema_invalid", envelope=tool_envelope(tool="fake.schema_invalid"))


def test_tool_executor_raises_when_tool_returns_ok_false(temp_project):
    profile = profile_with_tool("fake.tool_error", "tools/fake/tool_error.py")
    executor = ToolExecutor(project_root=temp_project, profile=profile)

    with pytest.raises(ToolReturnedError) as exc_info:
        executor.execute(tool_name="fake.tool_error", envelope=tool_envelope(tool="fake.tool_error"))

    assert exc_info.value.details["result"]["error"]["code"] == "FAKE_TOOL_ERROR"


def test_tool_executor_raises_on_non_zero_exit_code(temp_project):
    profile = profile_with_tool("fake.exit_code", "tools/fake/exit_code.py")
    executor = ToolExecutor(project_root=temp_project, profile=profile)

    with pytest.raises(ToolExecutionError) as exc_info:
        executor.execute(tool_name="fake.exit_code", envelope=tool_envelope(tool="fake.exit_code"))

    assert exc_info.value.details["returncode"] == 3


def test_tool_executor_logs_stderr_without_parsing_it(temp_project):
    profile = profile_with_tool("fake.stderr_log", "tools/fake/stderr_log.py")
    messages: list[str] = []
    executor = ToolExecutor(project_root=temp_project, profile=profile, log=messages.append)

    result = executor.execute(tool_name="fake.stderr_log", envelope=tool_envelope(tool="fake.stderr_log"))

    assert result.ok is True
    assert result.data == {"status": "ok"}
    assert any("human-only stderr log" in message for message in messages)
