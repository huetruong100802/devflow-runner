"""Pydantic models for profiles, workflows, and tool results."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolSpec(StrictModel):
    command: str = Field(min_length=1)
    args: list[str] = Field(default_factory=list)
    cwd: str | None = None
    timeout_seconds: int = Field(default=60, ge=1, le=3600)
    side_effect: bool = False
    env: dict[str, str] = Field(default_factory=dict)


class Profile(StrictModel):
    name: str = Field(min_length=1)
    organization: str | None = None
    project: str | None = None
    defaults: dict[str, Any] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)
    tools: dict[str, ToolSpec] = Field(default_factory=dict)

    @field_validator("tools")
    @classmethod
    def tool_names_must_be_non_empty(cls, value: dict[str, ToolSpec]) -> dict[str, ToolSpec]:
        for name in value:
            if not name.strip():
                raise ValueError("tool name must not be empty")
        return value


class WorkflowInput(StrictModel):
    description: str | None = None
    required: bool = False
    default: Any = None

    @model_validator(mode="after")
    def required_input_should_not_have_implicit_default(self) -> "WorkflowInput":
        # A required input may still define a default intentionally, but None does not satisfy it.
        return self


class WorkflowStep(StrictModel):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z_][A-Za-z0-9_\-]*$")
    tool: str = Field(min_length=1)
    name: str | None = None
    with_: dict[str, Any] = Field(default_factory=dict, alias="with")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Workflow(StrictModel):
    name: str = Field(min_length=1)
    description: str | None = None
    inputs: dict[str, WorkflowInput] = Field(default_factory=dict)
    steps: list[WorkflowStep] = Field(default_factory=list, min_length=1)
    outputs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("steps")
    @classmethod
    def step_ids_must_be_unique(cls, value: list[WorkflowStep]) -> list[WorkflowStep]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for step in value:
            if step.id in seen:
                duplicates.append(step.id)
            seen.add(step.id)
        if duplicates:
            raise ValueError(f"duplicate step id(s): {', '.join(sorted(set(duplicates)))}")
        return value


class ToolResult(StrictModel):
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None

    @classmethod
    def dry_run_plan(cls, *, tool: str, inputs: dict[str, Any], skipped: bool) -> "ToolResult":
        message = "side-effect tool skipped in dry-run" if skipped else "dry-run plan"
        return cls(
            ok=True,
            data={
                "dry_run": True,
                "skipped": skipped,
                "planned_tool": tool,
                "planned_inputs": inputs,
            },
            warnings=[message] if skipped else [],
            metrics={},
        )


class StepArtifact(StrictModel):
    id: str
    tool: str
    dry_run: bool
    skipped: bool = False
    inputs: dict[str, Any]
    result: ToolResult


JsonScalar = str | int | float | bool | None
InputValue = JsonScalar | list[Any] | dict[str, Any]
RunMode = Literal["validate", "run"]
