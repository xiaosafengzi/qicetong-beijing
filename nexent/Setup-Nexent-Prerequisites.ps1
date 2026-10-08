[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)) {
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"' + $PSCommandPath + '"')
    )
    return
}

$logPath = Join-Path $PSScriptRoot "prerequisite-latest.log"
Start-Transcript -Path $logPath -Force | Out-Null

try {
    New-Item -ItemType Directory -Path "D:\DockerDesktopData","D:\NexentData" -Force | Out-Null

    Write-Host "正在启用适用于 Linux 的 Windows 子系统……"
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    if ($LASTEXITCODE -notin 0, 3010) {
        throw "启用 WSL 功能失败，退出码 $LASTEXITCODE"
    }

    Write-Host "正在启用虚拟机平台……"
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    if ($LASTEXITCODE -notin 0, 3010) {
        throw "启用虚拟机平台失败，退出码 $LASTEXITCODE"
    }

    Write-Host "Windows 功能已启用。请重启 Windows。"
    Write-Host "重启后再次运行本脚本，它会继续安装或更新 WSL2 内核。"

    wsl.exe --install --no-distribution --web-download
    if ($LASTEXITCODE -notin 0, 3010) {
        Write-Warning "WSL 内核将在重启后继续安装；当前退出码为 $LASTEXITCODE。"
    }

    wsl.exe --set-default-version 2
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "默认 WSL 版本将在重启后设置。"
    }

    Write-Host "重启后，在 Docker Desktop 的 Settings > Resources > Advanced 中将 Disk image location 设置为 D:\DockerDesktopData。"
    Write-Host "设置完成后运行 Start-Nexent.ps1。"
} finally {
    Stop-Transcript | Out-Null
}
