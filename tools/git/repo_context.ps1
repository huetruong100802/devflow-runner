. (Join-Path $PSScriptRoot "_common.ps1")

try {
    $envelope = Read-ToolEnvelope
    $inputs = $envelope.inputs
    $workspaceInput = Get-InputString -Inputs $inputs -Name "workspace" -Default "."
    $workspace = Resolve-WorkspacePath -Workspace $workspaceInput
    $repoRoot = Get-GitRepositoryRoot -Workspace $workspace

    $branchResult = Invoke-GitText -Workspace $repoRoot -Arguments @("branch", "--show-current") -AllowFailure $true
    $currentBranch = $branchResult.text
    if ([string]::IsNullOrWhiteSpace($currentBranch)) {
        $currentBranch = "DETACHED"
    }

    $remoteResult = Invoke-GitText -Workspace $repoRoot -Arguments @("remote", "get-url", "origin") -AllowFailure $true
    $remoteOrigin = $null
    if ($remoteResult.exit_code -eq 0 -and -not [string]::IsNullOrWhiteSpace($remoteResult.text)) {
        $remoteOrigin = $remoteResult.text
    }

    $upstreamResult = Invoke-GitText -Workspace $repoRoot -Arguments @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") -AllowFailure $true
    $upstreamBranch = $null
    if ($upstreamResult.exit_code -eq 0 -and -not [string]::IsNullOrWhiteSpace($upstreamResult.text)) {
        $upstreamBranch = $upstreamResult.text
    }

    $commit = (Invoke-GitText -Workspace $repoRoot -Arguments @("rev-parse", "HEAD")).text
    $shortCommit = (Invoke-GitText -Workspace $repoRoot -Arguments @("rev-parse", "--short", "HEAD")).text
    $commitSubject = (Invoke-GitText -Workspace $repoRoot -Arguments @("log", "-1", "--pretty=%s")).text
    $statusText = (Invoke-GitText -Workspace $repoRoot -Arguments @("status", "--porcelain") -AllowFailure $true).text
    $statusLines = @()
    if (-not [string]::IsNullOrWhiteSpace($statusText)) {
        $statusLines = $statusText -split "`n"
    }

    Write-ToolSuccess -Data @{
        workspace = $workspace
        repo_root = $repoRoot
        current_branch = $currentBranch
        upstream_branch = $upstreamBranch
        remote_origin = $remoteOrigin
        latest_commit = $commit
        latest_commit_short = $shortCommit
        latest_commit_subject = $commitSubject
        is_dirty = ($statusLines.Count -gt 0)
        status_count = $statusLines.Count
    } -Metrics @{
        git_status_entries = $statusLines.Count
    }
    exit 0
}
catch {
    Write-ToolError -Code "GIT_REPO_CONTEXT_FAILED" -Message $_.Exception.Message -Details @{}
    exit 0
}
