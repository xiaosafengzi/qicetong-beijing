[CmdletBinding()]
param(
    [string]$DataRoot = "D:\NexentData"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$nexentRoot = Join-Path $projectRoot "external\nexent-develop"
$dockerDesktop = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"
$bash = "D:\Git\bin\bash.exe"
$runtimeDir = Join-Path $projectRoot "runtime\nexent"
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$dockerCli = (Get-Command docker.exe -ErrorAction Stop).Source

function Test-DockerEngine {
    $probe = New-Object System.Diagnostics.Process
    $probe.StartInfo.FileName = $dockerCli
    $probe.StartInfo.Arguments = "info --format {{.ServerVersion}}"
    $probe.StartInfo.UseShellExecute = $false
    $probe.StartInfo.CreateNoWindow = $true
    $probe.StartInfo.RedirectStandardOutput = $true
    $probe.StartInfo.RedirectStandardError = $true
    $null = $probe.Start()
    if (-not $probe.WaitForExit(5000)) {
        $probe.Kill()
        $probe.WaitForExit()
        $probe.Dispose()
        return $false
    }
    $succeeded = $probe.ExitCode -eq 0
    $probe.Dispose()
    return $succeeded
}

if (-not (Test-Path -LiteralPath $nexentRoot)) {
    throw "未找到 Nexent 源码目录：$nexentRoot"
}
if (-not (Test-Path -LiteralPath $dockerDesktop)) {
    throw "未找到 Docker Desktop。"
}
if (-not (Test-Path -LiteralPath $bash)) {
    throw "未找到 Git Bash：$bash"
}

$wslVersion = & wsl.exe --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "WSL2 尚未就绪。请先以管理员身份运行 $PSScriptRoot\Setup-Nexent-Prerequisites.ps1，并按提示重启。"
}

New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null

$dockerReady = Test-DockerEngine

if (-not $dockerReady) {
    Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        if (Test-DockerEngine) {
            $dockerReady = $true
            break
        }
    }
}

if (-not $dockerReady) {
    throw "Docker 引擎在 120 秒内未就绪，请打开 Docker Desktop 查看错误。"
}

$systemDrive = Get-PSDrive -Name C
$settings = Get-Content -Raw -LiteralPath (Join-Path $env:APPDATA "Docker\settings-store.json") | ConvertFrom-Json
$diskFolder = $settings.CustomWslDistroDir
$relocatedDisk = $null
if ($diskFolder -and $diskFolder -match '^[D-Z]:') {
    $relocatedDisk = Get-ChildItem -LiteralPath $diskFolder -Filter "*.vhdx" -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
}
if ($systemDrive.Free -lt 20GB -and -not $relocatedDisk) {
    throw "C 盘空间不足，尚未确认 Docker 虚拟磁盘已迁移至其他盘。请先检查 Docker Desktop 的磁盘设置。"
}

$bashRoot = $DataRoot -replace "\\", "/"
$deployLog = Join-Path $runtimeDir "deploy.log"
$errorLog = Join-Path $runtimeDir "deploy.err.log"
$projectPython = $null
foreach ($candidate in @(
    (Join-Path $projectRoot '.venv312\Scripts\python.exe'),
    (Join-Path $projectRoot '.venv\Scripts\python.exe')
)) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    try {
        & $candidate -c 'import sys' 2>$null
        if ($LASTEXITCODE -eq 0) { $projectPython = $candidate; break }
    } catch { }
}
if (-not $projectPython) { throw 'No usable project Python found; see README.md.' }
& $projectPython (Join-Path $PSScriptRoot "prepare_windows_deploy.py")
if ($LASTEXITCODE -ne 0) { throw "Windows 部署适配失败。" }
$overlayImage = "qicetong/nexent:v2.6.0-local"
$overlayDir = Join-Path $PSScriptRoot "runtime-overlay"
& $dockerCli build --tag $overlayImage $overlayDir
if ($LASTEXITCODE -ne 0) { throw "Nexent 本地兼容镜像构建失败。" }
Write-Host "正在部署 Nexent，首次运行需下载镜像。日志：$deployLog"
$previousPathConversion = $env:MSYS_NO_PATHCONV
$previousOptionalPrefetch = $env:NEXENT_SKIP_OPTIONAL_PREFETCH
$previousOverlayImage = $env:QICETONG_NEXENT_IMAGE
$env:MSYS_NO_PATHCONV = "1"
$env:NEXENT_SKIP_OPTIONAL_PREFETCH = "1"
$env:QICETONG_NEXENT_IMAGE = $overlayImage
Push-Location $nexentRoot
try {
    $deploy = Start-Process -FilePath $bash -WorkingDirectory $nexentRoot -WindowStyle Hidden -Wait -PassThru `
        -ArgumentList @("deploy.sh", "--defaults", "docker", "--components", "infrastructure,application,supabase", `
        "--port-policy", "development", "--image-source", "mainland", "--sandbox-mode", "lightweight", `
        "--root-dir", ('"' + $bashRoot + '"')) `
        -RedirectStandardOutput $deployLog -RedirectStandardError $errorLog
    if ($deploy.ExitCode -ne 0) {
        $existingServicesReady = $false
        try {
            $serviceHealth = Invoke-RestMethod -Uri "http://127.0.0.1:5010/health/ready" -TimeoutSec 5
            $existingServicesReady = $serviceHealth.status -eq "ready"
        } catch {}
        if (-not $existingServicesReady) {
            throw "Nexent 部署失败，退出码 $($deploy.ExitCode)。请查看 $errorLog"
        }
        Write-Warning "部署脚本的后置步骤返回 $($deploy.ExitCode)，但现有 Nexent 服务已就绪；请运行 connect_qicetong.py 复验账户与工具绑定。"
    }
} finally {
    Pop-Location
    $env:MSYS_NO_PATHCONV = $previousPathConversion
    $env:NEXENT_SKIP_OPTIONAL_PREFETCH = $previousOptionalPrefetch
    $env:QICETONG_NEXENT_IMAGE = $previousOverlayImage
}

$webReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) { $webReady = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}
if (-not $webReady) { throw "部署命令已结束，但 Nexent 网页尚未通过检查，请查看 $deployLog。" }
Write-Host "Nexent 网页已通过访问检查：http://localhost:3000"
Write-Host "企策通 MCP 地址：http://host.docker.internal:8767/mcp"
