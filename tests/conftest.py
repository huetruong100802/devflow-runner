from __future__ import annotations

from pathlib import Path
import shutil

import pytest


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def temp_project(tmp_path: Path, repo_root: Path) -> Path:
    for name in ["profiles", "workflows", "tools"]:
        shutil.copytree(repo_root / name, tmp_path / name)
    (tmp_path / "runs").mkdir()
    return tmp_path
