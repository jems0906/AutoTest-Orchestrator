$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "start-local.ps1"
& $scriptPath -DatabaseMode postgres -AllowPostgresFallbackToSqlite
