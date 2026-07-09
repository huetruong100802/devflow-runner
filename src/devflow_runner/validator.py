"""Validation helpers for loaded DevFlow config."""

from __future__ import annotations

from .errors import ValidationError
from .models import Profile, Workflow


def validate_workflow_tools(profile: Profile, workflow: Workflow) -> None:
    missing = sorted({step.tool for step in workflow.steps if step.tool not in profile.tools})
    if missing:
        raise ValidationError(
            "workflow references tool(s) not defined in profile",
            details={"workflow": workflow.name, "profile": profile.name, "missing_tools": missing},
        )


def validate_profile(profile: Profile) -> None:
    # DFR-001..DFR-008 intentionally keep env validation minimal.
    # Real ADO/Git environment validation starts after this foundation slice.
    duplicate_commands = [name for name, tool in profile.tools.items() if not tool.command.strip()]
    if duplicate_commands:
        raise ValidationError(
            "profile contains tool(s) with empty command",
            details={"profile": profile.name, "tools": duplicate_commands},
        )
