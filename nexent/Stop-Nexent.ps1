[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$nexentRoot = Join-Path $projectRoot "external\nexent-develop"
if (-not (Test-Path -LiteralPath $nexentRoot)) { throw "未找到 Nexent 源码目录。" }
$containerNames = @(
    "nexent-config", "nexent-runtime", "nexent-mcp", "nexent-northbound", "nexent-web",
    "nexent-elasticsearch", "nexent-postgresql", "nexent-redis", "nexent-minio",
    "supabase-kong-mini", "supabase-auth-mini", "supabase-db-mini"
)
$running = @(docker ps --format "{{.Names}}")
if ($LASTEXITCODE -ne 0) { throw "无法连接 Docker 引擎。" }
$toStop = @($running | Where-Object { $_ -in $containerNames })
if ($toStop.Count -gt 0) {
    docker stop --time 30 @toStop
    if ($LASTEXITCODE -ne 0) { throw "部分 Nexent 容器停止失败。" }
}
Write-Host "Nexent 容器已停止，容器和数据均已保留。"
