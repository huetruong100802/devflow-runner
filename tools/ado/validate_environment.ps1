. (Join-Path $PSScriptRoot "_common.ps1")

try {
    $envelope = Read-ToolEnvelope
    $scope = Get-AdoScope -Inputs $envelope.inputs

    $extension = Invoke-AzJson -Arguments @(
        "extension", "show",
        "--name", "azure-devops",
        "--only-show-errors",
        "--output", "json"
    ) -FailureCode "ADO_EXTENSION_NOT_FOUND" -FailureMessage "Azure DevOps CLI extension is not installed. Run 'az extension add --name azure-devops'."

    $account = Invoke-AzJson -Arguments @(
        "account", "show",
        "--only-show-errors",
        "--output", "json"
    ) -FailureCode "AZ_LOGIN_REQUIRED" -FailureMessage "Azure CLI is not authenticated. Run 'az login'."

    $project = Invoke-AzJson -Arguments @(
        "devops", "project", "show",
        "--organization", $scope.organization,
        "--project", $scope.project,
        "--only-show-errors",
        "--output", "json"
    ) -FailureCode "ADO_PROJECT_UNAVAILABLE" -FailureMessage "Azure DevOps organization or project could not be accessed."

    $accountUser = Get-ObjectPropertyValue -Object $account -Name "user"
    Write-ToolSuccess -Data @{
        organization = $scope.organization
        project = @{
            id = Get-ObjectPropertyValue -Object $project -Name "id"
            name = Get-ObjectPropertyValue -Object $project -Name "name"
            state = Get-ObjectPropertyValue -Object $project -Name "state"
            visibility = Get-ObjectPropertyValue -Object $project -Name "visibility"
        }
        azure_devops_extension = @{
            name = Get-ObjectPropertyValue -Object $extension -Name "name"
            version = Get-ObjectPropertyValue -Object $extension -Name "version"
        }
        account = @{
            id = Get-ObjectPropertyValue -Object $account -Name "id"
            name = Get-ObjectPropertyValue -Object $account -Name "name"
            tenant_id = Get-ObjectPropertyValue -Object $account -Name "tenantId"
            user = @{
                name = Get-ObjectPropertyValue -Object $accountUser -Name "name"
                type = Get-ObjectPropertyValue -Object $accountUser -Name "type"
            }
        }
    } -Metrics @{ checks = 4 }
    exit 0
}
catch {
    Write-ToolError -Code "ADO_ENV_VALIDATION_FAILED" -Message $_.Exception.Message -Details @{}
    exit 0
}
