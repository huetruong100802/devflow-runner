from __future__ import annotations

import pytest

from devflow_runner.errors import ValidationError
from devflow_runner.loader import load_profile, load_workflow
from devflow_runner.models import Workflow


def test_load_profile(temp_project):
    profile = load_profile(temp_project, "industrial")

    assert profile.name == "industrial"
    assert profile.organization == "Industrial-nois"
    assert "fake.echo" in profile.tools


def test_load_workflow(temp_project):
    workflow = load_workflow(temp_project, "read-work-item-context")

    assert workflow.name == "read-work-item-context"
    assert workflow.steps[0].id == "echo_context"
    assert workflow.steps[0].with_["work_item"] == "{{ inputs.work_item }}"


def test_workflow_rejects_unknown_field():
    with pytest.raises(Exception) as exc_info:
        Workflow.model_validate({
            "name": "bad",
            "steps": [{"id": "s1", "tool": "fake.echo"}],
            "parallel": True,
        })

    assert "Extra inputs are not permitted" in str(exc_info.value)


def test_load_profile_rejects_name_mismatch(temp_project):
    bad = temp_project / "profiles" / "mismatch.yml"
    bad.write_text("name: other\ntools: {}\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_profile(temp_project, "mismatch")
