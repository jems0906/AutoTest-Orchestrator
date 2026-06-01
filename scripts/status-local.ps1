$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $projectRoot ".run"
$backendPidFile = Join-Path $runDir "backend.pid"
$frontendPidFile = Join-Path $runDir "frontend.pid"

function Get-PidStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PidFile
    )

    if (-not (Test-Path $PidFile)) {
        return @{ exists = $false; pid = $null; running = $false }
    }

    $pidValue = Get-Content -Path $PidFile -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace($pidValue)) {
        return @{ exists = $true; pid = $null; running = $false }
    }

    $pidInt = [int]$pidValue
    $running = $null -ne (Get-Process -Id $pidInt -ErrorAction SilentlyContinue)
    return @{ exists = $true; pid = $pidInt; running = $running }
}

function Get-ListeningPid {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        $listeningPid = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty OwningProcess
        if ($listeningPid) {
            return $listeningPid
        }
    }
    catch {
        # Fallback below.
    }

    try {
        $lines = netstat -ano -p tcp | Select-String "LISTENING"
        foreach ($line in $lines) {
            if ($line.Line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
                return [int]$Matches[1]
            }
        }
    }
    catch {
        return $null
    }

    return $null
}

function Test-Http {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return $response.StatusCode
    }
    catch {
        return $null
    }
}

$backendStatus = Get-PidStatus -PidFile $backendPidFile
$frontendStatus = Get-PidStatus -PidFile $frontendPidFile

if (-not $backendStatus.pid) {
    $backendDetectedPid = Get-ListeningPid -Port 8000
    if ($backendDetectedPid) {
        $backendStatus.pid = $backendDetectedPid
        $backendStatus.running = $true
    }
}

if (-not $frontendStatus.pid) {
    $frontendDetectedPid = Get-ListeningPid -Port 5173
    if ($frontendDetectedPid) {
        $frontendStatus.pid = $frontendDetectedPid
        $frontendStatus.running = $true
    }
}

$backendHealth = Test-Http -Url "http://127.0.0.1:8000/health"
$frontendHealth = Test-Http -Url "http://127.0.0.1:5173"

Write-Output "Backend PID file: $($backendStatus.exists)"
Write-Output "Backend PID: $($backendStatus.pid)"
Write-Output "Backend process running: $($backendStatus.running)"
Write-Output "Backend HTTP status: $backendHealth"
Write-Output ""
Write-Output "Frontend PID file: $($frontendStatus.exists)"
Write-Output "Frontend PID: $($frontendStatus.pid)"
Write-Output "Frontend process running: $($frontendStatus.running)"
Write-Output "Frontend HTTP status: $frontendHealth"
