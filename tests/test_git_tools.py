from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def _require_git_and_pwsh() -> tuple[str, str]:
    git = shutil.which("git")
    pwsh = shutil.which("pwsh")
    if git is None or pwsh is None:
        pytest.skip("git and pwsh are required for Git tool integration tests")
    return git, pwsh


def _run(cmd: list[str], *, cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _init_repo(path: Path) -> None:
    git, _pwsh = _require_git_and_pwsh()
    _run([git, "init", "-b", "main"], cwd=path)
    _run([git, "config", "user.email", "devflow@example.local"], cwd=path)
    _run([git, "config", "user.name", "DevFlow Test"], cwd=path)
    (path / "README.md").write_text("base\n", encoding="utf-8")
    _run([git, "add", "README.md"], cwd=path)
    _run([git, "commit", "-m", "base"], cwd=path)
    _run([git, "checkout", "-b", "feature/test"], cwd=path)
    (path / "README.md").write_text("base\nchange\n", encoding="utf-8")
    (path / "src.txt").write_text("new\n", encoding="utf-8")
    _run([git, "add", "README.md", "src.txt"], cwd=path)
    _run([git, "commit", "-m", "feature change"], cwd=path)


def _envelope(tool: str, inputs: dict) -> str:
    return json.dumps({
        "meta": {"workflow": "test", "step": "step", "tool": tool, "dry_run": False},
        "context": {"run_id": "run", "run_dir": "runs/run", "workflow": "test", "profile": "industrial", "dry_run": False},
        "inputs": inputs,
    })


def _run_tool(script: Path, tool: str, inputs: dict, *, cwd: Path) -> dict:
    _git, pwsh = _require_git_and_pwsh()
    completed = subprocess.run(
        [pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        input=_envelope(tool, inputs),
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return json.loads(completed.stdout)


def test_git_repo_context_returns_repository_metadata(tmp_path: Path, repo_root: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    _init_repo(workspace)

    result = _run_tool(
        repo_root / "tools" / "git" / "repo_context.ps1",
        "git.repo_context",
        {"workspace": str(workspace)},
        cwd=repo_root,
    )

    assert result["ok"] is True
    assert Path(result["data"]["repo_root"]).resolve() == workspace.resolve()
    assert result["data"]["current_branch"] == "feature/test"
    assert result["data"]["latest_commit_subject"] == "feature change"
    assert result["data"]["is_dirty"] is False


def test_git_compact_diff_returns_line_capped_diff(tmp_path: Path, repo_root: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    _init_repo(workspace)

    result = _run_tool(
        repo_root / "tools" / "git" / "compact_diff.ps1",
        "git.compact_diff",
        {"workspace": str(workspace), "base_ref": "main", "max_lines": 3, "context_lines": 0},
        cwd=repo_root,
    )

    assert result["ok"] is True
    assert result["data"]["base_ref"] == "main"
    assert result["data"]["file_count"] == 2
    assert result["data"]["truncated"] is True
    assert "diff --git" in result["data"]["diff"]
    assert "diff truncated" in result["data"]["diff"]


def test_git_tools_return_protocol_error_for_missing_workspace(tmp_path: Path, repo_root: Path):
    missing = tmp_path / "missing"

    result = _run_tool(
        repo_root / "tools" / "git" / "repo_context.ps1",
        "git.repo_context",
        {"workspace": str(missing)},
        cwd=repo_root,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "WORKSPACE_NOT_FOUND"
