[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = "D:\NexentData\ollama"
$metadataFile = Join-Path $root "installation.json"
if (-not (Test-Path -LiteralPath $metadataFile)) { throw "本地模型安装尚未完成。" }
$metadata = Get-Content -Raw -LiteralPath $metadataFile | ConvertFrom-Json
$executable = $metadata.executable
if (-not (Test-Path -LiteralPath $executable)) { throw "Ollama 程序不存在：$executable" }

$env:OLLAMA_MODELS = Join-Path $root "models"
$env:OLLAMA_HOST = "127.0.0.1:11434"
New-Item -ItemType Directory -Path $env:OLLAMA_MODELS -Force | Out-Null
$runtimeDir = Join-Path (Split-Path -Parent $PSScriptRoot) "runtime\nexent"
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

$ready = $false
try {
    $version = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 2
    $ready = [bool]$version.version
} catch {}
if (-not $ready) {
    $server = Start-Process -FilePath $executable -ArgumentList "serve" -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDir "ollama-serve.log") `
        -RedirectStandardError (Join-Path $runtimeDir "ollama-serve.err.log")
    $server.Id | Set-Content -LiteralPath (Join-Path $runtimeDir "ollama-serve.pid")
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 1
        try {
            $version = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 2
            if ($version.version) { $ready = $true; break }
        } catch {}
    }
}
if (-not $ready) { throw "Ollama 本地服务未启动。" }

$models = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 8
if (-not @($models.models | Where-Object { $_.name -eq $metadata.model }).Count) {
    Write-Host "正在下载 $($metadata.model) 到 D 盘；日志：$runtimeDir\ollama-pull.log"
    $pull = Start-Process -FilePath $executable -ArgumentList @("pull", $metadata.model) -Wait -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $runtimeDir "ollama-pull.log") `
        -RedirectStandardError (Join-Path $runtimeDir "ollama-pull.err.log")
    if ($pull.ExitCode -ne 0) { throw "本地模型下载失败，退出码 $($pull.ExitCode)。" }
}
$models = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 8
if (-not @($models.models | Where-Object { $_.name -eq $metadata.model }).Count) {
    throw "模型未出现在本地列表。"
}
Write-Host "本地模型已就绪：$($metadata.model)"
