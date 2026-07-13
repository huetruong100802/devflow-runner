# DevFlow Runner

Thin Python CLI workflow runner for the first DevFlow MVP foundation tasks: DFR-001 to DFR-021.

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
- Azure DevOps tools:
  - `ado.validate_environment`: checks Azure CLI, the Azure DevOps extension, login state, organization and project access.
  - `ado.read_work_item`: reads one work item and returns stable summary fields plus the raw Azure DevOps payload.
  - `ado.create_pr`: creates a pull request and defaults to draft mode.
  - `ado.add_pr_reviewer`: adds one or more reviewers to a pull request.
  - `ado.link_work_item_to_pr`: links one or more work items to a pull request.

Not implemented in this slice:

- AI wrapper.
- End-to-end ADO workflows such as `create-pr` and `read-work-item-context` using the real ADO tools.
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

ADO tools additionally require:

- Azure CLI command `az` available on `PATH`.
- Azure DevOps extension installed with `az extension add --name azure-devops`.
- An active Azure CLI login from `az login`.
- Access to the organization and project configured in the selected profile.
- No PAT or other secret stored in profile YAML.

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

## ADO tool input notes

All ADO tools accept `organization` as either an organization name such as `newoceanis` or a full URL. Names are normalized to `https://dev.azure.com/<organization>`.

| Tool | Required inputs | Optional inputs | Side effect |
|---|---|---|---|
| `ado.validate_environment` | `organization`, `project` | none | no |
| `ado.read_work_item` | `organization`, `project`, `work_item` | none | no |
| `ado.create_pr` | `organization`, `project`, `repository`, `source_branch`, `target_branch`, `title` | `description`, `draft` (default `true`) | yes |
| `ado.add_pr_reviewer` | `organization`, `pull_request_id`, `reviewers` or `reviewer` | none | yes |
| `ado.link_work_item_to_pr` | `organization`, `pull_request_id`, `work_items` or `work_item` | none | yes |

The three mutation tools are registered with `side_effect: true`, so the runner skips them and records planned inputs when the containing workflow runs with `--dry-run`.
