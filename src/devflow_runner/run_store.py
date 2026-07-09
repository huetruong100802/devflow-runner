"""Run artifact writer."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_name(value: str) -> str:
    return _SAFE_NAME_RE.sub("-", value).strip("-") or "run"


class RunStore:
    def __init__(self, runs_root: Path, workflow_name: str) -> None:
        self.runs_root = runs_root
        self.workflow_name = workflow_name
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        short_id = uuid.uuid4().hex[:8]
        self.run_id = f"{timestamp}_{safe_name(workflow_name)}_{short_id}"
        self.run_dir = runs_root / self.run_id
        self.steps_dir = self.run_dir / "steps"
        self.steps_dir.mkdir(parents=True, exist_ok=False)
        self.log_path = self.run_dir / "log.txt"
        self.log_path.write_text("", encoding="utf-8")

    def write_json(self, relative_path: str, data: Any) -> Path:
        path = self.run_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def write_step(self, step_id: str, data: Any) -> Path:
        return self.write_json(f"steps/{safe_name(step_id)}.json", data)

    def append_log(self, message: str) -> None:
        if not message:
            return
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(message)
            if not message.endswith("\n"):
                handle.write("\n")
