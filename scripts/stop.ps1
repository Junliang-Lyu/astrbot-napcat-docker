$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$envArgs = @()
if (Test-Path ".env") {
    $envArgs = @("--env-file", ".env")
}

docker compose @envArgs down
