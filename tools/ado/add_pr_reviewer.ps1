. (Join-Path $PSScriptRoot "_common.ps1")

try {
    $envelope = Read-ToolEnvelope
    $inputs = $envelope.inputs
    $organizationInput = Get-RequiredInputString -Inputs $inputs -Name "organization"
    $organization = Normalize-AdoOrganization -Organization $organizationInput
    $pullRequestId = Get-RequiredInputInt -Inputs $inputs -Name "pull_request_id"
    $reviewers = @(Get-RequiredInputStringArray -Inputs $inputs -Name "reviewers" -Alias "reviewer")

    $arguments = @(
        "repos", "pr", "reviewer", "add",
        "--id", [string]$pullRequestId,
        "--reviewers"
    ) + $reviewers + @(
        "--organization", $organization,
        "--only-show-errors",
        "--output", "json"
    )

    $result = @(Invoke-AzJson -Arguments $arguments)

    Write-ToolSuccess -Data @{
        pull_request_id = $pullRequestId
        requested_reviewers = $reviewers
        reviewers = $result
    } -Metrics @{ reviewers_added = $reviewers.Count }
    exit 0
}
catch {
    Write-ToolError -Code "ADO_ADD_PR_REVIEWER_FAILED" -Message $_.Exception.Message -Details @{}
    exit 0
}
