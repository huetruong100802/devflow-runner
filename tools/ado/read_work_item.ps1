. (Join-Path $PSScriptRoot "_common.ps1")

try {
    $envelope = Read-ToolEnvelope
    $inputs = $envelope.inputs
    $scope = Get-AdoScope -Inputs $inputs
    $workItemId = Get-RequiredInputInt -Inputs $inputs -Name "work_item"

    $workItem = Invoke-AzJson -Arguments @(
        "boards", "work-item", "show",
        "--id", [string]$workItemId,
        "--organization", $scope.organization,
        "--project", $scope.project,
        "--expand", "relations",
        "--only-show-errors",
        "--output", "json"
    )

    $fields = Get-ObjectPropertyValue -Object $workItem -Name "fields"
    $assignedToValue = Get-ObjectPropertyValue -Object $fields -Name "System.AssignedTo"
    $assignedTo = $null
    if ($null -ne $assignedToValue) {
        if ($assignedToValue -is [string]) {
            $assignedTo = @{ display_name = [string]$assignedToValue; unique_name = $null }
        }
        else {
            $assignedTo = @{
                display_name = Get-ObjectPropertyValue -Object $assignedToValue -Name "displayName"
                unique_name = Get-ObjectPropertyValue -Object $assignedToValue -Name "uniqueName"
            }
        }
    }

    Write-ToolSuccess -Data @{
        id = Get-ObjectPropertyValue -Object $workItem -Name "id"
        rev = Get-ObjectPropertyValue -Object $workItem -Name "rev"
        url = Get-ObjectPropertyValue -Object $workItem -Name "url"
        title = Get-ObjectPropertyValue -Object $fields -Name "System.Title"
        state = Get-ObjectPropertyValue -Object $fields -Name "System.State"
        work_item_type = Get-ObjectPropertyValue -Object $fields -Name "System.WorkItemType"
        assigned_to = $assignedTo
        fields = $fields
        relations = Get-ObjectPropertyValue -Object $workItem -Name "relations"
        work_item = $workItem
    } -Metrics @{ work_items_read = 1 }
    exit 0
}
catch {
    Write-ToolError -Code "ADO_READ_WORK_ITEM_FAILED" -Message $_.Exception.Message -Details @{}
    exit 0
}
