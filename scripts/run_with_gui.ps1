Param(
    [switch]$ForceResetCredentials
)

function Read-KeyFromEnvFile {
    param ($Path)
    if (-Not (Test-Path $Path)) {
        return @{}
    }
    $values = @{}
    foreach ($line in Get-Content $Path | Where-Object { -and -not $_.StartsWith('#') -and $_.Trim() -ne '' }) {
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $value = $parts[1].Trim().Trim("'\"")
            $values[$key] = $value
        }
    }
    return $values
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installerDir = Join-Path $scriptRoot "..\..\Downloads\transcribeflow-installer"
$installerDir = (Resolve-Path $installerDir).Path
$envFileCandidates = @(
    Join-Path $scriptRoot "install.local.env",
    Join-Path $scriptRoot "install.env",
    Join-Path $scriptRoot ".env",
    Join-Path $scriptRoot "..\.env"
)

$secrets = @{}
foreach ($candidate in $envFileCandidates) {
    $secrets = Read-KeyFromEnvFile -Path $candidate
    if ($secrets.Count) {
        break
    }
}

if (-Not $secrets.ContainsKey('OPENAI_API_KEY')) {
    $secrets['OPENAI_API_KEY'] = $env:OPENAI_API_KEY
}
if (-Not $secrets.ContainsKey('CREDENTIALS_SECRET_KEY')) {
    $secrets['CREDENTIALS_SECRET_KEY'] = $env:CREDENTIALS_SECRET_KEY
}
if (-Not $secrets.ContainsKey('RUNTIME_CREDENTIALS_KEY')) {
    $secrets['RUNTIME_CREDENTIALS_KEY'] = $env:RUNTIME_CREDENTIALS_KEY
}

if (-Not $secrets['OPENAI_API_KEY']) {
    Write-Error "OPENAI_API_KEY não encontrado. Defina no arquivo install.env ou exporte a variável."
    exit 1
}

if (-Not ($secrets['CREDENTIALS_SECRET_KEY'] -or $secrets['RUNTIME_CREDENTIALS_KEY'])) {
    Write-Error "CREDENTIALS_SECRET_KEY ou RUNTIME_CREDENTIALS_KEY não encontrado."
    exit 1
}

[Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $secrets['OPENAI_API_KEY'], 'Process')
[Environment]::SetEnvironmentVariable('CREDENTIALS_SECRET_KEY', $secrets['CREDENTIALS_SECRET_KEY'], 'Process')
if ($secrets['RUNTIME_CREDENTIALS_KEY']) {
    [Environment]::SetEnvironmentVariable('RUNTIME_CREDENTIALS_KEY', $secrets['RUNTIME_CREDENTIALS_KEY'], 'Process')
}

if (-not [Environment]::Is64BitOperatingSystem -or [Environment]::OSVersion.Version.Major -lt 10) {
    Write-Error "Requer Windows 10/11 x64. Versão atual: $([Environment]::OSVersion.Version)"
    exit 1
}

Push-Location $installerDir
if ($ForceResetCredentials) {
    Remove-Item ".\config\runtime_credentials.json" -ErrorAction SilentlyContinue
    Remove-Item ".\config\.credentials_secret.key" -ErrorAction SilentlyContinue
}

$checkScript = Join-Path $scriptRoot "check_install_prereqs.py"
python $checkScript
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    exit $LASTEXITCODE
}

Write-Host "Iniciando TranscribeFlow... aguarde e abra http://localhost:8000 quando tiver pronto."
Start-Process -FilePath ".\TranscribeFlow.exe" -NoNewWindow -WorkingDirectory $installerDir
Pop-Location

function Ensure-DesktopShortcut {
    $shell = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "TranscribeFlow GUI.lnk"
    if ((Test-Path $shortcutPath) -and ($ForceResetCredentials -eq $false)) {
        return
    }
    $target = "powershell.exe"
    $arguments = "-ExecutionPolicy Bypass -File `"$scriptRoot\run_with_gui.ps1`""
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $target
    $shortcut.Arguments = $arguments
    $shortcut.WorkingDirectory = $installerDir
    $shortcut.IconLocation = "$installerDir\TranscribeFlow.exe"
    $shortcut.Description = "Inicia o TranscribeFlow no modo GUI com o ambiente preparado."
    $shortcut.Save()
}

Ensure-DesktopShortcut
