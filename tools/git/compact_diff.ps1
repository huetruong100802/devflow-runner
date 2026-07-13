. (Join-Path $PSScriptRoot "_common.ps1")

function Convert-NameStatusLine {
    param([Parameter(Mandatory=$true)] [string] $Line)

    $parts = $Line -split "`t"
    if ($parts.Count -eq 0 -or [string]::IsNullOrWhiteSpace($parts[0])) {
        return $null
    }

    $status = $parts[0]
    if ($status.StartsWith("R") -or $status.StartsWith("C")) {
        return [ordered]@{
            status = $status
            old_path = if ($parts.Count -gt 1) { $parts[1] } else { $null }
            path = if ($parts.Count -gt 2) { $parts[2] } else { $null }
        }
    }

    return [ordered]@{
        status = $status
        path = if ($parts.Count -gt 1) { $parts[1] } else { $null }
    }
}

try {
    $envelope = Read-ToolEnvelope
    $inputs = $envelope.inputs
    $workspaceInput = Get-InputString -Inputs $inputs -Name "workspace" -Default "."
    $workspace = Resolve-WorkspacePath -Workspace $workspaceInput
    $repoRoot = Get-GitRepositoryRoot -Workspace $workspace

    $baseRef = Get-InputString -Inputs $inputs -Name "base_ref" -Default "HEAD~1"
    $maxLines = Get-InputInt -Inputs $inputs -Name "max_lines" -Default 800
    if ($maxLines -lt 1) {
        Write-ToolError -Code "INVALID_MAX_LINES" -Message "max_lines must be >= 1." -Details @{ max_lines = $maxLines }
        exit 0
    }

    $contextLines = Get-InputInt -Inputs $inputs -Name "context_lines" -Default 3
    if ($contextLines -lt 0) {
        Write-ToolError -Code "INVALID_CONTEXT_LINES" -Message "context_lines must be >= 0." -Details @{ context_lines = $contextLines }
        exit 0
    }

    $mergeBaseResult = Invoke-GitText -Workspace $repoRoot -Arguments @("merge-base", $baseRef, "HEAD") -AllowFailure $true
    if ($mergeBaseResult.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($mergeBaseResult.text)) {
        Write-ToolError -Code "GIT_MERGE_BASE_FAILED" -Message "Could not resolve merge-base between base_ref and HEAD." -Details @{ base_ref = $baseRef; git_output = $mergeBaseResult.text }
        exit 0
    }

    $mergeBase = $mergeBaseResult.text
    $nameStatusText = (Invoke-GitText -Workspace $repoRoot -Arguments @("diff", "--name-status", "--find-renames", $mergeBase, "HEAD") -AllowFailure $true).text
    $files = @()
    if (-not [string]::IsNullOrWhiteSpace($nameStatusText)) {
        foreach ($line in ($nameStatusText -split "`n")) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $file = Convert-NameStatusLine -Line $line
            if ($null -ne $file) { $files += $file }
        }
    }

    $diffText = (Invoke-GitText -Workspace $repoRoot -Arguments @("diff", "--unified=$contextLines", "--no-ext-diff", "--find-renames", $mergeBase, "HEAD") -AllowFailure $true).text
    $allLines = @()
    if (-not [string]::IsNullOrEmpty($diffText)) {
        $allLines = $diffText -split "`n"
    }

    $totalLines = $allLines.Count
    $truncated = $totalLines -gt $maxLines
    $returnedLines = $allLines
    if ($truncated) {
        $returnedLines = $allLines | Select-Object -First $maxLines
        $returnedLines += ""
        $returnedLines += "[devflow-runner] diff truncated at $maxLines of $totalLines lines"
    }

    $returnedDiff = ($returnedLines -join "`n").TrimEnd()

    Write-ToolSuccess -Data @{
        workspace = $workspace
        repo_root = $repoRoot
        base_ref = $baseRef
        head_ref = "HEAD"
        merge_base = $mergeBase
        max_lines = $maxLines
        context_lines = $contextLines
        total_lines = $totalLines
        returned_lines = $returnedLines.Count
        truncated = $truncated
        files = $files
        file_count = $files.Count
        diff = $returnedDiff
    } -Metrics @{
        file_count = $files.Count
        total_lines = $totalLines
        returned_lines = $returnedLines.Count
        truncated = $truncated
    }
    exit 0
}
catch {
    Write-ToolError -Code "GIT_COMPACT_DIFF_FAILED" -Message $_.Exception.Message -Details @{}
    exit 0
}
