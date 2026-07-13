. (Join-Path $PSScriptRoot "_common.ps1")

try {
    $envelope = Read-ToolEnvelope
    $inputs = $envelope.inputs
    $organizationInput = Get-RequiredInputString -Inputs $inputs -Name "organization"
    $organization = Normalize-AdoOrganization -Organization $organizationInput
    $pullRequestId = Get-RequiredInputInt -Inputs $inputs -Name "pull_request_id"
    $workItems = @(Get-RequiredInputIntArray -Inputs $inputs -Name "work_items" -Alias "work_item")
    $workItemArguments = @($workItems | ForEach-Object { [string]$_ })

    $arguments = @(
        "repos", "pr", "work-item", "add",
        "--id", [string]$pullRequestId,
        "--work-items"
    ) + $workItemArguments + @(
        "--organization", $organization,
        "--only-show-errors",
        "--output", "json"
    )

    $result = @(Invoke-AzJson -Arguments $arguments)

    Write-ToolSuccess -Data @{
        pull_request_id = $pullRequestId
        work_items = $workItems
        links = $result
    } -Metrics @{ work_items_linked = $workItems.Count }
    exit 0
}
catch {
    Write-ToolError -Code "ADO_LINK_WORK_ITEM_FAILED" -Message $_.Exception.Message -Details @{}
    exit 0
}
