"""Command line interface for DevFlow Runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .errors import DevFlowError
from .runner import WorkflowRunner


def parse_input_pair(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("input must be in key=value format")
    key, raw = value.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError("input key must not be empty")
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return key, parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wf", description="DevFlow Runner CLI")
    parser.add_argument("--version", action="version", version=f"wf {__version__}")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root containing profiles/, workflows/, tools/, runs/. Default: current directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate profile and workflow YAML.")
    validate.add_argument("--profile", required=True, help="Profile name from profiles/<name>.yml")
    validate.add_argument("--workflow", help="Optional workflow name from workflows/<name>.yml")

    run = subparsers.add_parser("run", help="Run a workflow.")
    run.add_argument("workflow", help="Workflow name from workflows/<name>.yml")
    run.add_argument("--profile", required=True, help="Profile name from profiles/<name>.yml")
    run.add_argument("--dry-run", action="store_true", help="Skip side-effect tools and emit planned inputs.")
    run.add_argument(
        "--input",
        dest="inputs",
        action="append",
        type=parse_input_pair,
        default=[],
        help="Workflow input in key=value form. Repeatable. JSON values are accepted.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.project_root)
    runner = WorkflowRunner(project_root=project_root)

    try:
        if args.command == "validate":
            result = runner.validate(profile_name=args.profile, workflow_name=args.workflow)
        elif args.command == "run":
            inputs = dict(args.inputs)
            result = runner.run(
                workflow_name=args.workflow,
                profile_name=args.profile,
                inputs=inputs,
                dry_run=args.dry_run,
            ).to_dict()
        else:
            parser.error(f"unknown command: {args.command}")
            return 2
    except DevFlowError as exc:
        print(json.dumps({"ok": False, "error": exc.to_dict()}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
