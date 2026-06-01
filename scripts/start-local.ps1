param(
    [ValidateSet("postgres", "sqlite")]
    [string]$DatabaseMode = "postgres",
    [switch]$AllowPostgresFallbackToSqlite
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $projectRoot ".run"
$backendPidFile = Join-Path $runDir "backend.pid"
$frontendPidFile = Join-Path $runDir "frontend.pid"
$backendLog = Join-Path $runDir "backend.log"
$backendErrLog = Join-Path $runDir "backend.err.log"
$frontendLog = Join-Path $runDir "frontend.log"
$frontendErrLog = Join-Path $runDir "frontend.err.log"
$databaseModeFile = Join-Path $runDir "database.mode"

if (-not (Test-Path $runDir)) {
    New-Item -ItemType Directory -Path $runDir | Out-Null
}

function Test-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$Attempts = 30,
        [int]$DelayMs = 500
    )

    for ($i = 0; $i -lt $Attempts; $i++) {
        if (Test-HttpReady -Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds $DelayMs
    }

    return $false
}

function Test-TcpPortOpen {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Host,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect($Host, $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(1500, $false)
        if (-not $connected) {
            $client.Close()
            return $false
        }

        $client.EndConnect($async)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Wait-TcpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Host,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$Attempts = 30,
        [int]$DelayMs = 1000
    )

    for ($i = 0; $i -lt $Attempts; $i++) {
        if (Test-TcpPortOpen -Host $Host -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds $DelayMs
    }

    return $false
}

function Initialize-Postgres {
    param(
        [switch]$AllowFallback
    )

    try {
        Set-Location $projectRoot
        docker compose up -d postgres | Out-Null
    }
    catch {
        if ($AllowFallback) {
            Write-Warning "PostgreSQL startup failed; falling back to SQLite mode."
            return @{ mode = "sqlite"; url = "sqlite:///./autotest_local.db" }
        }
        throw "Failed to start PostgreSQL via Docker Compose. Ensure Docker is running or use -DatabaseMode sqlite."
    }

    if (-not (Wait-TcpReady -Host "127.0.0.1" -Port 5432 -Attempts 45 -DelayMs 1000)) {
        if ($AllowFallback) {
            Write-Warning "PostgreSQL did not become ready; falling back to SQLite mode."
            return @{ mode = "sqlite"; url = "sqlite:///./autotest_local.db" }
        }
        throw "PostgreSQL did not become ready on port 5432."
    }

    return @{ mode = "postgres"; url = "postgresql+psycopg://autotest:autotest@127.0.0.1:5432/autotest" }
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

$resolvedDb = if ($DatabaseMode -eq "postgres") {
    Initialize-Postgres -AllowFallback:$AllowPostgresFallbackToSqlite.IsPresent
}
else {
    @{ mode = "sqlite"; url = "sqlite:///./autotest_local.db" }
}

Set-Content -Path $databaseModeFile -Value $resolvedDb.mode

# Backend
if (Test-HttpReady -Url "http://127.0.0.1:8000/health") {
    $existingBackendPid = Get-ListeningPid -Port 8000
    if ($existingBackendPid) {
        Set-Content -Path $backendPidFile -Value $existingBackendPid
    }
    Write-Output "Backend already running on http://127.0.0.1:8000"
}
else {
    $backendWorkdir = Join-Path $projectRoot "backend"
    $env:DATABASE_URL = $resolvedDb.url

    $backendProcess = Start-Process python -ArgumentList @(
        "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"
    ) -WorkingDirectory $backendWorkdir -PassThru -RedirectStandardOutput $backendLog -RedirectStandardError $backendErrLog

    Set-Content -Path $backendPidFile -Value $backendProcess.Id

    if (-not (Wait-HttpReady -Url "http://127.0.0.1:8000/health")) {
        throw "Backend failed to become ready. Check $backendLog"
    }

    Write-Output "Backend started on http://127.0.0.1:8000 (PID $($backendProcess.Id))"
}

# Frontend
if (Test-HttpReady -Url "http://127.0.0.1:5173") {
    $existingFrontendPid = Get-ListeningPid -Port 5173
    if ($existingFrontendPid) {
        Set-Content -Path $frontendPidFile -Value $existingFrontendPid
    }
    Write-Output "Frontend already running on http://127.0.0.1:5173"
}
else {
    $frontendWorkdir = Join-Path $projectRoot "frontend"

    $frontendProcess = Start-Process python -ArgumentList @(
        "-m", "http.server", "5173"
    ) -WorkingDirectory $frontendWorkdir -PassThru -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErrLog

    Set-Content -Path $frontendPidFile -Value $frontendProcess.Id

    if (-not (Wait-HttpReady -Url "http://127.0.0.1:5173")) {
        throw "Frontend failed to become ready. Check $frontendLog"
    }

    Write-Output "Frontend started on http://127.0.0.1:5173 (PID $($frontendProcess.Id))"
}

Write-Output ""
Write-Output "Database mode: $($resolvedDb.mode)"
Write-Output "Open dashboard: http://127.0.0.1:5173"
Write-Output "Open API docs: http://127.0.0.1:8000/docs"
