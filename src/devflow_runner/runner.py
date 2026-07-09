"""Workflow runner implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .loader import load_profile, load_workflow
from .models import Profile, StepArtifact, ToolContext, ToolEnvelope, ToolMeta, ToolResult, Workflow, WorkflowStep
from .resolver import VariableResolver
from .run_store import RunStore
from .tool_exec import ToolExecutor
from .validator import validate_profile, validate_workflow_tools


@dataclass(frozen=True)
class RunSummary:
    ok: bool
    workflow: str
    profile: str
    run_id: str
    run_dir: Path
    output: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "workflow": self.workflow,
            "profile": self.profile,
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "output": self.output,
        }


class WorkflowRunner:
    def __init__(self, *, project_root: Path, runs_root: Path | None = None) -> None:
        self.project_root = project_root.resolve()
        self.runs_root = (runs_root or self.project_root / "runs").resolve()
        self.resolver = VariableResolver()

    def validate(self, *, profile_name: str, workflow_name: str | None = None) -> dict[str, Any]:
        profile = load_profile(self.project_root, profile_name)
        validate_profile(profile)
        workflow_names: list[str] = []
        if workflow_name:
            workflow = load_workflow(self.project_root, workflow_name)
            validate_workflow_tools(profile, workflow)
            workflow_names.append(workflow.name)
        else:
            workflows_dir = self.project_root / "workflows"
            for workflow_file in sorted(workflows_dir.glob("*.yml")):
                workflow = load_workflow(self.project_root, workflow_file.stem)
                validate_workflow_tools(profile, workflow)
                workflow_names.append(workflow.name)
        return {
            "ok": True,
            "profile": profile.name,
            "workflows": workflow_names,
            "tools": sorted(profile.tools),
        }

    def run(self, *, workflow_name: str, profile_name: str, inputs: dict[str, Any], dry_run: bool) -> RunSummary:
        profile = load_profile(self.project_root, profile_name)
        validate_profile(profile)
        workflow = load_workflow(self.project_root, workflow_name)
        validate_workflow_tools(profile, workflow)

        effective_inputs = self._build_inputs(workflow, inputs)
        store = RunStore(self.runs_root, workflow.name)
        context = ToolContext(
            run_id=store.run_id,
            run_dir=str(store.run_dir),
            workflow=workflow.name,
            profile=profile.name,
            dry_run=dry_run,
        )
        steps_scope: dict[str, dict[str, Any]] = {}
        executor = ToolExecutor(project_root=self.project_root, profile=profile, log=store.append_log)

        store.write_json(
            "input.json",
            {
                "workflow": workflow.name,
                "profile": profile.name,
                "dry_run": dry_run,
                "inputs": effective_inputs,
            },
        )
        store.write_json("context.json", context.model_dump(mode="json"))

        for step in workflow.steps:
            artifact = self._run_step(
                step=step,
                workflow=workflow,
                profile=profile,
                context=context,
                inputs=effective_inputs,
                steps_scope=steps_scope,
                executor=executor,
                dry_run=dry_run,
            )
            store.write_step(step.id, artifact.model_dump(mode="json"))
            steps_scope[step.id] = {
                "output": artifact.result.data,
                "result": artifact.result.model_dump(mode="json"),
            }

        output_scope = self._scope(profile=profile, inputs=effective_inputs, steps=steps_scope)
        output = self.resolver.resolve(workflow.outputs, output_scope) if workflow.outputs else {
            step_id: value["output"] for step_id, value in steps_scope.items()
        }
        store.write_json("output.json", output)

        return RunSummary(
            ok=True,
            workflow=workflow.name,
            profile=profile.name,
            run_id=store.run_id,
            run_dir=store.run_dir,
            output=output,
        )

    def _run_step(
        self,
        *,
        step: WorkflowStep,
        workflow: Workflow,
        profile: Profile,
        context: ToolContext,
        inputs: dict[str, Any],
        steps_scope: dict[str, dict[str, Any]],
        executor: ToolExecutor,
        dry_run: bool,
    ) -> StepArtifact:
        scope = self._scope(profile=profile, inputs=inputs, steps=steps_scope)
        resolved_inputs = self.resolver.resolve(step.with_, scope)
        tool_spec = profile.tools[step.tool]

        if dry_run and tool_spec.side_effect:
            result = ToolResult.dry_run_plan(tool=step.tool, inputs=resolved_inputs, skipped=True)
            return StepArtifact(
                id=step.id,
                tool=step.tool,
                dry_run=True,
                skipped=True,
                inputs=resolved_inputs,
                result=result,
            )

        envelope = ToolEnvelope(
            meta=ToolMeta(
                workflow=workflow.name,
                step=step.id,
                tool=step.tool,
                dry_run=dry_run,
            ),
            context=context,
            inputs=resolved_inputs,
        )
        result = executor.execute(tool_name=step.tool, envelope=envelope)
        return StepArtifact(
            id=step.id,
            tool=step.tool,
            dry_run=dry_run,
            skipped=False,
            inputs=resolved_inputs,
            result=result,
        )

    def _scope(self, *, profile: Profile, inputs: dict[str, Any], steps: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return {
            "inputs": inputs,
            "profile": profile.model_dump(mode="json"),
            "steps": steps,
        }

    def _build_inputs(self, workflow: Workflow, raw_inputs: dict[str, Any]) -> dict[str, Any]:
        effective: dict[str, Any] = {}
        for name, spec in workflow.inputs.items():
            if name in raw_inputs:
                effective[name] = raw_inputs[name]
            elif spec.default is not None:
                effective[name] = spec.default
            elif spec.required:
                raise ValidationError(
                    f"missing required input '{name}'",
                    details={"workflow": workflow.name, "input": name},
                )
            else:
                effective[name] = None

        for name, value in raw_inputs.items():
            if name not in workflow.inputs:
                raise ValidationError(
                    f"unknown input '{name}' for workflow '{workflow.name}'",
                    details={"workflow": workflow.name, "input": name},
                )
            effective[name] = value
        return effective
