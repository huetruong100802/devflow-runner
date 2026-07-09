from __future__ import annotations

import pytest

from devflow_runner.errors import ToolProtocolError
from devflow_runner.loader import load_profile
from devflow_runner.models import Profile, ToolSpec
from devflow_runner.tool_exec import ToolExecutor


def test_tool_executor_parses_json_stdout(temp_project):
    profile = load_profile(temp_project, "industrial")
    executor = ToolExecutor(project_root=temp_project, profile=profile)

    result = executor.execute(
        tool_name="fake.echo",
        envelope={"meta": {}, "context": {}, "inputs": {"hello": "world"}},
    )

    assert result.ok is True
    assert result.data == {"hello": "world"}
    assert result.metrics["input_keys"] == 1


def test_tool_executor_rejects_invalid_json_stdout(temp_project):
    profile = Profile(
        name="bad-profile",
        tools={
            "fake.bad": ToolSpec(
                command="python",
                args=["tools/fake/bad_stdout.py"],
                timeout_seconds=30,
            )
        },
    )
    executor = ToolExecutor(project_root=temp_project, profile=profile)

    with pytest.raises(ToolProtocolError):
        executor.execute(tool_name="fake.bad", envelope={"meta": {}, "context": {}, "inputs": {}})
