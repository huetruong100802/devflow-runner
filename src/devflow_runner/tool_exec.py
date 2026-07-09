"""Subprocess tool execution."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError as PydanticValidationError

from .errors import ToolExecutionError, ToolProtocolError, ToolReturnedError
from .models import Profile, ToolEnvelope, ToolResult

LogFn = Callable[[str], None]


class ToolExecutor:
    def __init__(self, *, project_root: Path, profile: Profile, log: LogFn | None = None) -> None:
        self.project_root = project_root
        self.profile = profile
        self.log = log or (lambda _message: None)

    def execute(self, *, tool_name: str, envelope: ToolEnvelope | dict[str, Any]) -> ToolResult:
        if tool_name not in self.profile.tools:
            raise ToolExecutionError(
                f"tool '{tool_name}' is not defined in profile '{self.profile.name}'",
                details={"tool": tool_name, "profile": self.profile.name},
            )

        try:
            tool_envelope = ToolEnvelope.model_validate(envelope)
        except PydanticValidationError as exc:
            raise ToolProtocolError(
                f"tool '{tool_name}' input envelope does not match ToolEnvelope schema",
                details={"tool": tool_name, "errors": exc.errors(include_url=False)},
            ) from exc

        if tool_envelope.meta.tool != tool_name:
            raise ToolProtocolError(
                f"tool envelope meta.tool does not match requested tool '{tool_name}'",
                details={"tool": tool_name, "meta_tool": tool_envelope.meta.tool},
            )

        tool = self.profile.tools[tool_name]
        command = [tool.command, *tool.args]
        cwd = self._resolve_cwd(tool.cwd)
        env = os.environ.copy()
        env.update(self.profile.env)
        env.update(tool.env)

        try:
            completed = subprocess.run(
                command,
                input=json.dumps(tool_envelope.model_dump(mode="json"), ensure_ascii=False),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(cwd),
                env=env,
                timeout=tool.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolExecutionError(
                f"tool '{tool_name}' timed out after {tool.timeout_seconds}s",
                details={"tool": tool_name, "timeout_seconds": tool.timeout_seconds},
            ) from exc
        except OSError as exc:
            raise ToolExecutionError(
                f"failed to start tool '{tool_name}': {exc}",
                details={"tool": tool_name, "command": command},
            ) from exc

        if completed.stderr:
            self.log(f"[tool:{tool_name}:stderr]\n{completed.stderr.rstrip()}\n")

        stdout = completed.stdout.strip()
        if not stdout:
            raise ToolProtocolError(
                f"tool '{tool_name}' did not write JSON to stdout",
                details={"tool": tool_name, "returncode": completed.returncode},
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ToolProtocolError(
                f"tool '{tool_name}' stdout is not valid JSON",
                details={"tool": tool_name, "stdout": completed.stdout[:1000]},
            ) from exc

        try:
            result = ToolResult.model_validate(payload)
        except PydanticValidationError as exc:
            raise ToolProtocolError(
                f"tool '{tool_name}' stdout does not match ToolResult schema",
                details={"tool": tool_name, "errors": exc.errors(include_url=False), "stdout": payload},
            ) from exc

        if completed.returncode != 0:
            raise ToolExecutionError(
                f"tool '{tool_name}' exited with code {completed.returncode}",
                details={"tool": tool_name, "returncode": completed.returncode, "result": result.model_dump(mode="json")},
            )

        if not result.ok:
            error = result.error
            error_message = error.message if error is not None else "tool returned ok=false"
            raise ToolReturnedError(
                f"tool '{tool_name}' returned error: {error_message}",
                details={"tool": tool_name, "result": result.model_dump(mode="json")},
            )

        return result

    def _resolve_cwd(self, cwd: str | None) -> Path:
        if cwd is None:
            return self.project_root
        path = Path(cwd)
        if not path.is_absolute():
            path = self.project_root / path
        return path
