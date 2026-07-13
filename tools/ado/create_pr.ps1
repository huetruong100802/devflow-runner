. (Join-Path $PSScriptRoot "_common.ps1")

try {
    $envelope = Read-ToolEnvelope
    $inputs = $envelope.inputs
    $scope = Get-AdoScope -Inputs $inputs
    $repository = Get-RequiredInputString -Inputs $inputs -Name "repository"
    $sourceBranch = Get-RequiredInputString -Inputs $inputs -Name "source_branch"
    $targetBranch = Get-RequiredInputString -Inputs $inputs -Name "target_branch"
    $title = Get-RequiredInputString -Inputs $inputs -Name "title"
    $description = Get-OptionalInputString -Inputs $inputs -Name "description" -Default ""
    $draft = Get-OptionalInputBool -Inputs $inputs -Name "draft" -Default $true

    $arguments = @(
        "repos", "pr", "create",
        "--repository", $repository,
        "--source-branch", $sourceBranch,
        "--target-branch", $targetBranch,
        "--title", $title,
        "--draft", $draft.ToString().ToLowerInvariant(),
        "--organization", $scope.organization,
        "--project", $scope.project,
        "--only-show-errors",
        "--output", "json"
    )
    if (-not [string]::IsNullOrWhiteSpace($description)) {
        $arguments += @("--description", $description)
    }

    $pullRequest = Invoke-AzJson -Arguments $arguments

    Write-ToolSuccess -Data @{
        pull_request_id = Get-ObjectPropertyValue -Object $pullRequest -Name "pullRequestId"
        status = Get-ObjectPropertyValue -Object $pullRequest -Name "status"
        is_draft = Get-ObjectPropertyValue -Object $pullRequest -Name "isDraft"
        url = Get-ObjectPropertyValue -Object $pullRequest -Name "url"
        repository = $repository
        source_branch = $sourceBranch
        target_branch = $targetBranch
        pull_request = $pullRequest
    } -Metrics @{ pull_requests_created = 1 }
    exit 0
}
catch {
    Write-ToolError -Code "ADO_CREATE_PR_FAILED" -Message $_.Exception.Message -Details @{}
    exit 0
}
