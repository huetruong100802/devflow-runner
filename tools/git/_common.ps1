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

function Get-InputString {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name,
        [string] $Default = $null
    )

    if ($null -ne $Inputs.PSObject.Properties[$Name] -and $null -ne $Inputs.$Name) {
        return [string]$Inputs.$Name
    }
    return $Default
}

function Get-InputInt {
    param(
        [Parameter(Mandatory=$true)] $Inputs,
        [Parameter(Mandatory=$true)] [string] $Name,
        [int] $Default
    )

    if ($null -eq $Inputs.PSObject.Properties[$Name] -or $null -eq $Inputs.$Name -or [string]::IsNullOrWhiteSpace([string]$Inputs.$Name)) {
        return $Default
    }

    try {
        $value = [int]$Inputs.$Name
    }
    catch {
        throw "Input '$Name' must be an integer."
    }

    return $value
}

function Resolve-WorkspacePath {
    param([string] $Workspace)

    if ([string]::IsNullOrWhiteSpace($Workspace)) {
        $Workspace = "."
    }

    return [System.IO.Path]::GetFullPath($Workspace)
}

function Invoke-GitText {
    param(
        [Parameter(Mandatory=$true)] [string] $Workspace,
        [Parameter(Mandatory=$true)] [string[]] $Arguments,
        [bool] $AllowFailure = $false
    )

    $output = & git -C $Workspace @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | ForEach-Object { $_.ToString() }) -join "`n"
    $text = $text.Trim()

    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "git $($Arguments -join ' ') failed with exit code ${exitCode}: $text"
    }

    return [ordered]@{
        exit_code = $exitCode
        text = $text
    }
}

function Get-GitRepositoryRoot {
    param([Parameter(Mandatory=$true)] [string] $Workspace)

    if (-not (Test-Path -LiteralPath $Workspace)) {
        Write-ToolError -Code "WORKSPACE_NOT_FOUND" -Message "Workspace path does not exist." -Details @{ workspace = $Workspace }
        exit 0
    }

    if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) {
        Write-ToolError -Code "WORKSPACE_NOT_DIRECTORY" -Message "Workspace path is not a directory." -Details @{ workspace = $Workspace }
        exit 0
    }

    $rootResult = Invoke-GitText -Workspace $Workspace -Arguments @("rev-parse", "--show-toplevel") -AllowFailure $true
    if ($rootResult.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($rootResult.text)) {
        Write-ToolError -Code "NOT_GIT_REPOSITORY" -Message "Workspace is not inside a Git repository." -Details @{ workspace = $Workspace; git_output = $rootResult.text }
        exit 0
    }

    return $rootResult.text
}
