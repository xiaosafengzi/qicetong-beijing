param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$projectPython = $null
foreach ($candidate in @(
    (Join-Path $projectRoot '.venv312\Scripts\python.exe'),
    (Join-Path $projectRoot '.venv\Scripts\python.exe')
)) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    try {
        & $candidate -c 'import fastapi, mcp, pypdf' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $projectPython = $candidate
            break
        }
    } catch { }
}
if (-not $projectPython) {
    throw 'No usable project Python environment found. Install requirements.txt into .venv or .venv312; see README.md.'
}
$projectRuntime = Join-Path $projectRoot 'runtime'
New-Item -ItemType Directory -Path $projectRuntime -Force | Out-Null
$projectRunning = $false
try {
    $projectHealth = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 2
    $projectRunning = $projectHealth.mode -eq 'local_evidence_review'
} catch { }
if (-not $projectRunning) {
    $projectWeb = Start-Process -FilePath $projectPython -ArgumentList @('-m','uvicorn','qicetong.app:app','--host','127.0.0.1','--port','8765') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRuntime 'web.log') -RedirectStandardError (Join-Path $projectRuntime 'web.err.log')
    $projectWeb.Id | Set-Content -LiteralPath (Join-Path $projectRuntime 'web.pid')
}
$projectMcpRunning = Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
if (-not $projectMcpRunning) {
    $projectMcp = Start-Process -FilePath $projectPython -ArgumentList @('-m','qicetong.mcp_server') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRuntime 'mcp.log') -RedirectStandardError (Join-Path $projectRuntime 'mcp.err.log')
    $projectMcp.Id | Set-Content -LiteralPath (Join-Path $projectRuntime 'mcp.pid')
}
$projectMcpHttpRunning = Get-NetTCPConnection -LocalPort 8767 -State Listen -ErrorAction SilentlyContinue
if (-not $projectMcpHttpRunning) {
    $projectMcpHttp = Start-Process -FilePath $projectPython -ArgumentList @('-m','qicetong.mcp_http_server') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRuntime 'mcp-http.log') -RedirectStandardError (Join-Path $projectRuntime 'mcp-http.err.log')
    $projectMcpHttp.Id | Set-Content -LiteralPath (Join-Path $projectRuntime 'mcp-http.pid')
}
for ($projectAttempt = 0; $projectAttempt -lt 25; $projectAttempt++) {
    try {
        $projectHealth = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 1
        if ($projectHealth.status -eq 'ok') { break }
    } catch { Start-Sleep -Milliseconds 400 }
}
if (-not $projectHealth -or $projectHealth.status -ne 'ok') {
    throw 'Service did not start. Inspect runtime/web.err.log.'
}
Write-Output 'Qicetong: http://127.0.0.1:8765'
Write-Output 'MCP SSE: http://127.0.0.1:8766/sse'
Write-Output 'MCP HTTP: http://127.0.0.1:8767/mcp'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:8765' }
