param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$envArgs = @()
if (Test-Path ".env") {
    $envArgs = @("--env-file", ".env")
}

$argsList = @("compose") + $envArgs
if ($Build) {
    $argsList += @("up", "-d", "--build")
} else {
    $argsList += @("up", "-d")
}

docker @argsList

Write-Host ""
Write-Host "AstrBot WebUI: http://localhost:6185"
Write-Host "NapCat WebUI:  http://localhost:6099/webui"
Write-Host "Logs:"
Write-Host "  docker compose logs -f astrbot"
Write-Host "  docker compose logs -f napcat"
