from __future__ import annotations

import json

from devflow_runner.runner import WorkflowRunner


def test_runner_creates_artifacts_for_read_work_item_context(temp_project):
    runner = WorkflowRunner(project_root=temp_project)

    summary = runner.run(
        workflow_name="read-work-item-context",
        profile_name="industrial",
        inputs={"work_item": "6219", "workspace": "dxfactory"},
        dry_run=True,
    )

    assert summary.ok is True
    assert summary.output["work_item"] == "6219"
    assert summary.output["workspace"] == "dxfactory"
    assert (summary.run_dir / "input.json").exists()
    assert (summary.run_dir / "context.json").exists()
    assert (summary.run_dir / "steps" / "echo_context.json").exists()
    assert (summary.run_dir / "output.json").exists()
    assert (summary.run_dir / "log.txt").exists()


def test_dry_run_skips_side_effect_tool(temp_project):
    runner = WorkflowRunner(project_root=temp_project)

    summary = runner.run(
        workflow_name="side-effect-dry-run",
        profile_name="industrial",
        inputs={"value": "abc"},
        dry_run=True,
    )

    assert summary.output == {
        "planned_tool": "fake.mutate",
        "skipped": True,
        "value": "abc",
    }
    step_artifact = json.loads((summary.run_dir / "steps" / "planned_mutation.json").read_text(encoding="utf-8"))
    assert step_artifact["skipped"] is True
    assert step_artifact["result"]["data"]["planned_tool"] == "fake.mutate"
