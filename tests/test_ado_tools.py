from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ADO_TOOL_SPECS = {
    "ado.validate_environment": ("tools/ado/validate_environment.ps1", False),
    "ado.read_work_item": ("tools/ado/read_work_item.ps1", False),
    "ado.create_pr": ("tools/ado/create_pr.ps1", True),
    "ado.add_pr_reviewer": ("tools/ado/add_pr_reviewer.ps1", True),
    "ado.link_work_item_to_pr": ("tools/ado/link_work_item_to_pr.ps1", True),
}


def _require_pwsh() -> str:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("PowerShell 7 is required for ADO tool integration tests")
    return pwsh


def _envelope(tool: str, inputs: dict) -> str:
    return json.dumps(
        {
            "meta": {"workflow": "test", "step": "step", "tool": tool, "dry_run": False},
            "context": {
                "run_id": "run",
                "run_dir": "runs/run",
                "workflow": "test",
                "profile": "industrial",
                "dry_run": False,
            },
            "inputs": inputs,
        }
    )


def _write_fake_az(bin_dir: Path) -> Path:
    fake = bin_dir / "fake_az.py"
    fake.write_text(
        r'''
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
log_path = Path(os.environ["FAKE_AZ_LOG"])
with log_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\n")

fail_prefix = os.environ.get("FAKE_AZ_FAIL_PREFIX", "")
if fail_prefix and " ".join(args).startswith(fail_prefix):
    print(os.environ.get("FAKE_AZ_FAIL_MESSAGE", "fake az failure"), file=sys.stderr)
    raise SystemExit(int(os.environ.get("FAKE_AZ_FAIL_CODE", "1")))

if args[:2] == ["extension", "show"]:
    payload = {"name": "azure-devops", "version": "1.0.0"}
elif args[:2] == ["account", "show"]:
    payload = {"id": "subscription-id", "name": "Test Subscription", "tenantId": "tenant-id", "user": {"name": "dev@example.com", "type": "user"}}
elif args[:3] == ["devops", "project", "show"]:
    payload = {"id": "project-id", "name": "DxFactory", "state": "wellFormed", "visibility": "private"}
elif args[:3] == ["boards", "work-item", "show"]:
    payload = {"id": 6219, "rev": 7, "url": "https://dev.azure.com/example/_apis/wit/workItems/6219", "fields": {"System.Title": "Fix duplicate material options", "System.State": "Active", "System.WorkItemType": "Bug", "System.AssignedTo": {"displayName": "Hue Truong", "uniqueName": "hue@example.com"}}}
elif args[:3] == ["repos", "pr", "create"]:
    payload = {"pullRequestId": 1958, "status": "active", "isDraft": True, "url": "https://dev.azure.com/example/_apis/git/pullRequests/1958"}
elif args[:4] == ["repos", "pr", "reviewer", "add"]:
    payload = [{"displayName": "Reviewer", "uniqueName": "reviewer@example.com", "vote": 0}]
elif args[:4] == ["repos", "pr", "work-item", "add"]:
    payload = [{"id": 6219, "url": "https://dev.azure.com/example/_apis/wit/workItems/6219"}]
else:
    print("unexpected fake az arguments: " + " ".join(args), file=sys.stderr)
    raise SystemExit(2)

print(json.dumps(payload))
'''.strip()
        + "\n",
        encoding="utf-8",
    )

    if os.name == "nt":
        launcher = bin_dir / "az.cmd"
        launcher.write_text(f'@"{sys.executable}" "{fake}" %*\r\n', encoding="utf-8")
    else:
        launcher = bin_dir / "az"
        launcher.write_text(f'#!{sys.executable}\nexec(open({str(fake)!r}, encoding="utf-8").read())\n', encoding="utf-8")
        launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return launcher


def _run_tool(repo_root: Path, script_name: str, tool: str, inputs: dict, tmp_path: Path, *, fail_prefix: str = "") -> tuple[dict, list[list[str]], str]:
    pwsh = _require_pwsh()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_az(bin_dir)
    log_path = tmp_path / "az.log"

    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["FAKE_AZ_LOG"] = str(log_path)
    if fail_prefix:
        env["FAKE_AZ_FAIL_PREFIX"] = fail_prefix

    completed = subprocess.run(
        [pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(repo_root / "tools" / "ado" / script_name)],
        input=_envelope(tool, inputs),
        cwd=repo_root,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    calls = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()] if log_path.exists() else []
    return json.loads(completed.stdout), calls, completed.stderr


@pytest.mark.parametrize("profile_name", ["industrial", "newoceanis"])
def test_profiles_register_all_phase4_ado_tools(repo_root: Path, profile_name: str):
    profile = yaml.safe_load((repo_root / "profiles" / f"{profile_name}.yml").read_text(encoding="utf-8"))

    for tool_name, (script_path, side_effect) in ADO_TOOL_SPECS.items():
        spec = profile["tools"][tool_name]
        assert spec["command"] == "pwsh"
        assert spec["args"][-1] == script_path
        assert spec["side_effect"] is side_effect


def test_validate_environment_checks_extension_login_and_project(repo_root: Path, tmp_path: Path):
    result, calls, _stderr = _run_tool(
        repo_root,
        "validate_environment.ps1",
        "ado.validate_environment",
        {"organization": "Industrial-nois", "project": "DxFactory"},
        tmp_path,
    )

    assert result["ok"] is True
    assert result["data"]["organization"] == "https://dev.azure.com/Industrial-nois"
    assert [call[:3] for call in calls] == [
        ["extension", "show", "--name"],
        ["account", "show", "--only-show-errors"],
        ["devops", "project", "show"],
    ]


def test_read_work_item_uses_profile_scope_and_returns_stable_fields(repo_root: Path, tmp_path: Path):
    result, calls, _stderr = _run_tool(
        repo_root,
        "read_work_item.ps1",
        "ado.read_work_item",
        {"organization": "Industrial-nois", "project": "DxFactory", "work_item": 6219},
        tmp_path,
    )

    assert result["ok"] is True
    assert result["data"]["id"] == 6219
    assert result["data"]["title"] == "Fix duplicate material options"
    assert result["data"]["assigned_to"]["display_name"] == "Hue Truong"
    call = calls[0]
    assert call[:3] == ["boards", "work-item", "show"]
    assert call[call.index("--organization") + 1] == "https://dev.azure.com/Industrial-nois"
    assert call[call.index("--project") + 1] == "DxFactory"


def test_create_pr_passes_exact_mutation_arguments(repo_root: Path, tmp_path: Path):
    result, calls, _stderr = _run_tool(
        repo_root,
        "create_pr.ps1",
        "ado.create_pr",
        {
            "organization": "newoceanis",
            "project": "DxFactory",
            "repository": "Backend-Fresh",
            "source_branch": "feature/6219",
            "target_branch": "dxfac/development",
            "title": "Fix #6219 duplicate material options",
            "description": "Summary body",
        },
        tmp_path,
    )

    assert result["ok"] is True
    assert result["data"]["pull_request_id"] == 1958
    call = calls[0]
    assert call[:3] == ["repos", "pr", "create"]
    assert call[call.index("--draft") + 1] == "true"
    assert call[call.index("--target-branch") + 1] == "dxfac/development"


def test_add_reviewer_accepts_single_or_multiple_reviewers(repo_root: Path, tmp_path: Path):
    result, calls, _stderr = _run_tool(
        repo_root,
        "add_pr_reviewer.ps1",
        "ado.add_pr_reviewer",
        {"organization": "newoceanis", "pull_request_id": 1958, "reviewers": ["a@example.com", "b@example.com"]},
        tmp_path,
    )

    assert result["ok"] is True
    assert result["data"]["requested_reviewers"] == ["a@example.com", "b@example.com"]
    call = calls[0]
    reviewers_index = call.index("--reviewers")
    assert call[reviewers_index + 1 : reviewers_index + 3] == ["a@example.com", "b@example.com"]


def test_link_work_item_accepts_single_work_item_alias(repo_root: Path, tmp_path: Path):
    result, calls, _stderr = _run_tool(
        repo_root,
        "link_work_item_to_pr.ps1",
        "ado.link_work_item_to_pr",
        {"organization": "newoceanis", "pull_request_id": 1958, "work_item": 6219},
        tmp_path,
    )

    assert result["ok"] is True
    assert result["data"]["work_items"] == [6219]
    call = calls[0]
    assert call[call.index("--work-items") + 1] == "6219"


def test_ado_command_failure_returns_tool_error_and_logs_stderr(repo_root: Path, tmp_path: Path):
    result, _calls, stderr = _run_tool(
        repo_root,
        "read_work_item.ps1",
        "ado.read_work_item",
        {"organization": "newoceanis", "project": "DxFactory", "work_item": 6219},
        tmp_path,
        fail_prefix="boards work-item show",
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "ADO_COMMAND_FAILED"
    assert result["error"]["details"]["exit_code"] == 1
    assert "fake az failure" in stderr
