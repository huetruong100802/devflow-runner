# DevFlow Runner

Thin Python CLI workflow runner for the first DevFlow MVP foundation tasks: DFR-001 to DFR-016.

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
- Git read-only tools:
  - `git.repo_context`: validates workspace and returns branch, repo root, remote and latest commit metadata.
  - `git.compact_diff`: validates workspace and returns a line-capped merge-base diff plus changed-file summary.

Not implemented in this slice:

- Real Azure DevOps mutation tools.
- AI wrapper.
- UI, scheduler, retry engine, plugin marketplace, parallel execution.

## Install for local development

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .[dev]
```

Git tools require:

- `git` available on `PATH`.
- PowerShell 7 command `pwsh` available on `PATH`.

## Commands

```bash
wf --help
wf validate --profile industrial
wf run read-work-item-context --profile industrial --input work_item=6219 --input workspace=dxfactory --dry-run
```

Git context workflow:

```bash
wf run git-context --profile industrial --input workspace=. --input base_ref=dxfac/development
```

Override the diff budget when needed:

```bash
wf run git-context --profile industrial --input workspace=. --input max_diff_lines=300
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

## Git tool output notes

`git.repo_context` returns stable metadata under `data`, including:

- `workspace`
- `repo_root`
- `current_branch`
- `upstream_branch`
- `remote_origin`
- `latest_commit`
- `latest_commit_short`
- `latest_commit_subject`
- `is_dirty`
- `status_count`

`git.compact_diff` returns:

- `base_ref`
- `head_ref`
- `merge_base`
- `diff`
- `files`
- `file_count`
- `total_lines`
- `returned_lines`
- `truncated`
