# DevFlow Runner

Thin Python CLI workflow runner for the first DevFlow MVP foundation tasks: DFR-001 to DFR-013.

Implemented scope:

- `wf` CLI package entrypoint.
- Profile YAML loading from `profiles/<name>.yml`.
- Workflow YAML loading from `workflows/<name>.yml`.
- Pydantic schema validation with explicit errors.
- Variable resolver for:
  - `{{ inputs.x }}`
  - `{{ profile.x }}` / `{{ profile.x.y }}`
  - `{{ steps.step_id.output.x }}`
- Run artifact writer:
  - `input.json`
  - `context.json`
  - `steps/<step_id>.json`
  - `output.json`
  - `log.txt`
- Tool subprocess executor:
  - sends validated JSON envelope to `stdin`
  - parses machine JSON from `stdout`
  - writes `stderr` to `log.txt`
  - fails fast on invalid stdout JSON
  - fails the step when a tool returns `ok: false`
- Dry-run handling for side-effect tools.

Not implemented in this slice:

- Real Azure DevOps mutation tools.
- Git tools.
- AI wrapper.
- UI, scheduler, retry engine, plugin marketplace, parallel execution.

## Install for local development

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Commands

```bash
wf --help
wf validate --profile industrial
wf run read-work-item-context --profile industrial --input work_item=6219 --input workspace=dxfactory --dry-run
```

## Tool contract

A tool is called as a subprocess. Runner sends a JSON envelope to `stdin`:

```json
{
  "meta": {
    "workflow": "read-work-item-context",
    "step": "echo_context",
    "tool": "fake.echo",
    "dry_run": false
  },
  "context": {
    "run_id": "...",
    "run_dir": "...",
    "workflow": "read-work-item-context",
    "profile": "industrial",
    "dry_run": false
  },
  "inputs": {
    "work_item": "6219"
  }
}
```

A successful tool must write machine JSON to `stdout`:

```json
{
  "ok": true,
  "data": { "key": "value" },
  "warnings": [],
  "metrics": {}
}
```

A tool-level failure must still write valid machine JSON to `stdout`:

```json
{
  "ok": false,
  "error": {
    "code": "ADO_LOGIN_REQUIRED",
    "message": "Please run az login",
    "details": {}
  },
  "metrics": {}
}
```

Runner treats this as a failed step. Human logs belong on `stderr` only and are never parsed as data.
