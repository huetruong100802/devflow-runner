"""Tiny template resolver for DevFlow YAML values."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .errors import ResolverError

_TOKEN_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")
_FULL_TOKEN_RE = re.compile(r"^{{\s*([^{}]+?)\s*}}$")


class VariableResolver:
    """Resolve `{{ inputs.x }}`, `{{ profile.x }}`, and `{{ steps.id.output.x }}`."""

    def resolve(self, value: Any, scope: Mapping[str, Any]) -> Any:
        if isinstance(value, str):
            return self._resolve_string(value, scope)
        if isinstance(value, list):
            return [self.resolve(item, scope) for item in value]
        if isinstance(value, dict):
            return {key: self.resolve(item, scope) for key, item in value.items()}
        return value

    def _resolve_string(self, value: str, scope: Mapping[str, Any]) -> Any:
        full_match = _FULL_TOKEN_RE.match(value)
        if full_match:
            return self._resolve_expr(full_match.group(1), scope)

        def replace(match: re.Match[str]) -> str:
            resolved = self._resolve_expr(match.group(1), scope)
            if resolved is None:
                return ""
            return str(resolved)

        return _TOKEN_RE.sub(replace, value)

    def _resolve_expr(self, expr: str, scope: Mapping[str, Any]) -> Any:
        parts = [part.strip() for part in expr.split(".") if part.strip()]
        if not parts:
            raise ResolverError("empty template expression")

        root = parts[0]
        if root not in {"inputs", "profile", "steps"}:
            raise ResolverError(
                f"unsupported template root '{root}'",
                details={"expr": expr, "allowed_roots": ["inputs", "profile", "steps"]},
            )

        current: Any = scope
        traversed: list[str] = []
        for part in parts:
            traversed.append(part)
            current = self._get_child(current, part, expr=expr, traversed=traversed)
        return current

    @staticmethod
    def _get_child(current: Any, part: str, *, expr: str, traversed: list[str]) -> Any:
        if isinstance(current, Mapping):
            if part not in current:
                raise ResolverError(
                    f"missing template value at '{'.'.join(traversed)}'",
                    details={"expr": expr, "missing": part},
                )
            return current[part]
        if isinstance(current, list):
            if not part.isdigit():
                raise ResolverError(
                    f"list template segment must be numeric at '{'.'.join(traversed)}'",
                    details={"expr": expr, "segment": part},
                )
            index = int(part)
            try:
                return current[index]
            except IndexError as exc:
                raise ResolverError(
                    f"list index out of range at '{'.'.join(traversed)}'",
                    details={"expr": expr, "index": index},
                ) from exc
        raise ResolverError(
            f"cannot traverse template value at '{'.'.join(traversed)}'",
            details={"expr": expr, "segment": part, "type": type(current).__name__},
        )
