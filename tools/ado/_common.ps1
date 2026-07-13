Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-ToolEnvelope {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        Write-ToolError -Code "EMPTY_STDIN" -Message "Tool expected JSON envelope on stdin." -Details @{}
        exit 2
    }

    try {
        return $raw | ConvertFrom-Json -Depth 50
    }
    catch {
        Write-ToolError -Code "BAD_STDIN_JSON" -Message $_.Exception.Message -Details @{}
        exit 2
    }
}

function Write-ToolSuccess {
    param(
        [Parameter(Mandatory=$true)] [hashtable] $Data,
        [string[]] $Warnings = @(),
        [hashtable] $Metrics = @{}
    )

    [ordered]@{
        ok = $true
        data = $Data
        warnings = $Warnings
        metrics = $Metrics
    } | ConvertTo-Json -Depth 50 -Compress
}

function Write-ToolError {
    param(
        [Parameter(Mandatory=$true)] [string] $Code,
        [Parameter(Mandatory=$true)] [string] $Message,
        [hashtable] $Details = @{},
        [hashtable] $Metrics = @{}
    )

    [ordered]@{
        ok = $false
        data = @{}
        warnings = @()
        metrics = $Metrics
        error = [ordered]@{
            code = $Code
            message = $Message
            details = $Details
        }
    } | ConvertTo-Json -Depth 50 -Compress
}

function Get-ObjectPropertyValue {
    param(
        $Object,
        [Parameter(Mandatory=$true)] [string] $Name
    )

    if ($null -eq $Object) {
        return $null
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function Get-InputValue {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name
    )

    return Get-ObjectPropertyValue -Object $Inputs -Name $Name
}

function Get-RequiredInputString {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name
    )

    $value = Get-InputValue -Inputs $Inputs -Name $Name
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        Write-ToolError -Code "ADO_INPUT_INVALID" -Message "Input '$Name' is required." -Details @{ input = $Name }
        exit 0
    }

    return ([string]$value).Trim()
}

function Get-OptionalInputString {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name,
        [string] $Default = $null
    )

    $value = Get-InputValue -Inputs $Inputs -Name $Name
    if ($null -eq $value) {
        return $Default
    }

    return [string]$value
}

function Get-RequiredInputInt {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name
    )

    $value = Get-InputValue -Inputs $Inputs -Name $Name
    $parsed = 0
    if ($null -eq $value -or -not [int]::TryParse([string]$value, [ref]$parsed) -or $parsed -le 0) {
        Write-ToolError -Code "ADO_INPUT_INVALID" -Message "Input '$Name' must be a positive integer." -Details @{ input = $Name; value = $value }
        exit 0
    }

    return $parsed
}

function Get-OptionalInputBool {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name,
        [bool] $Default = $false
    )

    $value = Get-InputValue -Inputs $Inputs -Name $Name
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        return $Default
    }

    if ($value -is [bool]) {
        return [bool]$value
    }

    $text = ([string]$value).Trim().ToLowerInvariant()
    if ($text -in @("true", "1", "yes")) {
        return $true
    }
    if ($text -in @("false", "0", "no")) {
        return $false
    }

    Write-ToolError -Code "ADO_INPUT_INVALID" -Message "Input '$Name' must be a boolean." -Details @{ input = $Name; value = $value }
    exit 0
}

function Get-RequiredInputStringArray {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name,
        [string] $Alias = $null
    )

    $value = Get-InputValue -Inputs $Inputs -Name $Name
    if ($null -eq $value -and -not [string]::IsNullOrWhiteSpace($Alias)) {
        $value = Get-InputValue -Inputs $Inputs -Name $Alias
    }

    $items = @()
    if ($value -is [string]) {
        $items = @(
            $value.Split(",", [System.StringSplitOptions]::RemoveEmptyEntries) |
                ForEach-Object { $_.Trim() } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        )
    }
    elseif ($value -is [System.Collections.IEnumerable]) {
        $items = @(
            $value |
                ForEach-Object { ([string]$_).Trim() } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        )
    }
    elseif ($null -ne $value) {
        $scalar = ([string]$value).Trim()
        if (-not [string]::IsNullOrWhiteSpace($scalar)) {
            $items = @($scalar)
        }
    }

    if ($items.Count -eq 0) {
        $accepted = if ([string]::IsNullOrWhiteSpace($Alias)) { $Name } else { "$Name or $Alias" }
        Write-ToolError -Code "ADO_INPUT_INVALID" -Message "Input '$accepted' must contain at least one value." -Details @{ input = $Name; alias = $Alias }
        exit 0
    }

    return $items
}

function Get-RequiredInputIntArray {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name,
        [string] $Alias = $null
    )

    $rawItems = @(Get-RequiredInputStringArray -Inputs $Inputs -Name $Name -Alias $Alias)
    $items = @()
    foreach ($rawItem in $rawItems) {
        $parsed = 0
        if (-not [int]::TryParse([string]$rawItem, [ref]$parsed) -or $parsed -le 0) {
            Write-ToolError -Code "ADO_INPUT_INVALID" -Message "Input '$Name' must contain only positive integers." -Details @{ input = $Name; value = $rawItem }
            exit 0
        }
        $items += $parsed
    }

    return $items
}

function Normalize-AdoOrganization {
    param([Parameter(Mandatory=$true)] [string] $Organization)

    $value = $Organization.Trim().TrimEnd([char]"/")
    if ($value -match "^https?://") {
        return $value
    }

    return "https://dev.azure.com/$value"
}

function Get-AzCommandPath {
    $command = Get-Command az -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        Write-ToolError -Code "AZ_CLI_NOT_FOUND" -Message "Azure CLI command 'az' was not found on PATH." -Details @{}
        exit 0
    }

    return $command.Source
}

function Invoke-AzJson {
    param(
        [Parameter(Mandatory=$true)] [string[]] $Arguments,
        [string] $FailureCode = "ADO_COMMAND_FAILED",
        [string] $FailureMessage = "Azure CLI command failed."
    )

    $azCommand = Get-AzCommandPath
    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        & $azCommand @Arguments 1> $stdoutPath 2> $stderrPath
        $exitCode = $LASTEXITCODE
        $stdout = [System.IO.File]::ReadAllText($stdoutPath).Trim()
        $stderr = [System.IO.File]::ReadAllText($stderrPath).Trim()

        if (-not [string]::IsNullOrWhiteSpace($stderr)) {
            [Console]::Error.WriteLine($stderr)
        }

        if ($exitCode -ne 0) {
            Write-ToolError -Code $FailureCode -Message $FailureMessage -Details @{
                command = @("az") + $Arguments
                exit_code = $exitCode
                stderr = $stderr
            }
            exit 0
        }

        if ([string]::IsNullOrWhiteSpace($stdout)) {
            Write-ToolError -Code "ADO_INVALID_JSON" -Message "Azure CLI command returned empty stdout; JSON was expected." -Details @{
                command = @("az") + $Arguments
            }
            exit 0
        }

        try {
            return $stdout | ConvertFrom-Json -Depth 100
        }
        catch {
            Write-ToolError -Code "ADO_INVALID_JSON" -Message "Azure CLI command did not return valid JSON." -Details @{
                command = @("az") + $Arguments
                stdout = $stdout.Substring(0, [Math]::Min($stdout.Length, 1000))
            }
            exit 0
        }
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

function Get-AdoScope {
    param([Parameter(Mandatory=$true)] $Inputs)

    $organizationInput = Get-RequiredInputString -Inputs $Inputs -Name "organization"
    $project = Get-RequiredInputString -Inputs $Inputs -Name "project"

    return @{
        organization = Normalize-AdoOrganization -Organization $organizationInput
        project = $project
    }
}
