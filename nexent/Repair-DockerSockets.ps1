[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$backendLog = Join-Path $env:LOCALAPPDATA "Docker\log\host\com.docker.backend.exe.log"
$recent = (Get-Content -LiteralPath $backendLog -Tail 250) -join "`n"
if ($recent -notmatch 'starting services: initializing.*listening on unix://.*The file cannot be accessed by the system') {
    throw "The known Docker socket failure was not found in the recent log. No repair was performed."
}
if (Get-Process -Name @("com.docker.backend", "Docker Desktop") -ErrorAction SilentlyContinue) {
    throw "Exit Docker Desktop before repairing its socket directories."
}

# Preserve every original socket directory; never delete Docker data or credentials.
$directories = @(
    (Join-Path $env:LOCALAPPDATA "Docker\run"),
    (Join-Path $env:LOCALAPPDATA "docker-secrets-engine")
)
foreach ($socketDirectory in $directories) {
    if (-not (Test-Path -LiteralPath $socketDirectory)) { continue }
    $items = @(Get-ChildItem -LiteralPath $socketDirectory -Force)
    if ($items | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) }) {
        throw "The socket directory contains regular files and was preserved: $socketDirectory"
    }
    Rename-Item -LiteralPath $socketDirectory -NewName ((Split-Path $socketDirectory -Leaf) + "-stale-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    New-Item -ItemType Directory -Path $socketDirectory | Out-Null
}
Write-Host "Stale Docker socket directories were isolated and preserved. Docker Desktop can be restarted."
