"""YAML loading helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError as PydanticValidationError

from .errors import ConfigError, ValidationError
from .models import Profile, Workflow

TModel = TypeVar("TModel", bound=BaseModel)


def read_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"YAML file not found: {path}", details={"path": str(path)})
    if not path.is_file():
        raise ConfigError(f"YAML path is not a file: {path}", details={"path": str(path)})

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}", details={"path": str(path)}) from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigError(f"YAML root must be an object: {path}", details={"path": str(path)})
    return loaded


def parse_model(model_type: type[TModel], data: dict[str, Any], *, path: Path) -> TModel:
    try:
        return model_type.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(
            f"Invalid {model_type.__name__} YAML: {path}",
            details={"path": str(path), "errors": exc.errors(include_url=False)},
        ) from exc


def load_profile(project_root: Path, name: str) -> Profile:
    path = project_root / "profiles" / f"{name}.yml"
    profile = parse_model(Profile, read_yaml_file(path), path=path)
    if profile.name != name:
        raise ValidationError(
            f"Profile file name '{name}' does not match profile.name '{profile.name}'",
            details={"path": str(path), "expected": name, "actual": profile.name},
        )
    return profile


def load_workflow(project_root: Path, name: str) -> Workflow:
    path = project_root / "workflows" / f"{name}.yml"
    workflow = parse_model(Workflow, read_yaml_file(path), path=path)
    if workflow.name != name:
        raise ValidationError(
            f"Workflow file name '{name}' does not match workflow.name '{workflow.name}'",
            details={"path": str(path), "expected": name, "actual": workflow.name},
        )
    return workflow


def load_all_workflows(project_root: Path) -> list[Workflow]:
    workflows_dir = project_root / "workflows"
    if not workflows_dir.exists():
        raise ConfigError(f"workflows directory not found: {workflows_dir}", details={"path": str(workflows_dir)})
    workflows: list[Workflow] = []
    for path in sorted(workflows_dir.glob("*.yml")):
        workflows.append(parse_model(Workflow, read_yaml_file(path), path=path))
    return workflows
