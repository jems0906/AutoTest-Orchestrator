$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $projectRoot ".run"
$backendPidFile = Join-Path $runDir "backend.pid"
$frontendPidFile = Join-Path $runDir "frontend.pid"

function Stop-ByPidFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PidFile,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (-not (Test-Path $PidFile)) {
        Write-Output "$Label PID file not found."
        return
    }

    $pidValue = Get-Content -Path $PidFile -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace($pidValue)) {
        Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
        Write-Output "$Label PID file was empty and has been removed."
        return
    }

    $pidInt = [int]$pidValue
    $process = Get-Process -Id $pidInt -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        Stop-Process -Id $pidInt -Force
        Write-Output "$Label stopped (PID $pidInt)."
    }
    else {
        Write-Output "$Label process with PID $pidInt not found."
    }

    Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
}

function Stop-ByPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique

        if ($connections) {
            foreach ($pid in $connections) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Output "$Label port fallback stop: killed PID $pid on port $Port."
            }
        }
    }
    catch {
        # Fallback below.
    }

    try {
        $pids = @()
        $lines = netstat -ano -p tcp | Select-String "LISTENING"
        foreach ($line in $lines) {
            if ($line.Line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
                $pids += [int]$Matches[1]
            }
        }

        $uniquePids = $pids | Select-Object -Unique
        foreach ($pid in $uniquePids) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Output "$Label netstat fallback stop: killed PID $pid on port $Port."
        }
    }
    catch {
        # No-op if netstat parsing fails.
    }
}

Stop-ByPidFile -PidFile $backendPidFile -Label "Backend"
Stop-ByPidFile -PidFile $frontendPidFile -Label "Frontend"

Stop-ByPort -Port 8000 -Label "Backend"
Stop-ByPort -Port 5173 -Label "Frontend"

Write-Output "Local services stop routine completed."
