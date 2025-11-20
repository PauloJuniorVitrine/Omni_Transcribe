Param(
    [switch]$ForceResetCredentials
)

function Import-EnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return @{} }
    $values = @{}
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $value = $parts[1].Trim().Trim("'`\"")
            if ($key) { $values[$key] = $value }
        }
    }
    return $values
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installerDir = Resolve-Path (Join-Path $scriptRoot '..\..\Downloads\transcribeflow-installer') -ErrorAction SilentlyContinue
if (-not $installerDir) {
    Write-Error 'Installer directory not found. Copy TranscribeFlow.exe into Downloads\transcribeflow-installer'
    exit 1
}
$installerDir = $installerDir.Path

$envFiles = @(
    Join-Path $scriptRoot 'install.local.env',
    Join-Path $scriptRoot 'install.env',
    Join-Path $scriptRoot '.env',
    Join-Path $scriptRoot '..\.env'
)
$secrets = @{}
foreach ($candidate in $envFiles) {
    $secrets = Import-EnvFile -Path $candidate
    if ($secrets.Count) { break }
}

if (-not $secrets['OPENAI_API_KEY']) {
    $secrets['OPENAI_API_KEY'] = $env:OPENAI_API_KEY
}
if (-not $secrets['CREDENTIALS_SECRET_KEY']) {
    $secrets['CREDENTIALS_SECRET_KEY'] = $env:CREDENTIALS_SECRET_KEY
}

if (-not $secrets['OPENAI_API_KEY']) {
    Write-Error 'OPENAI_API_KEY missing in install.env or environment.'
    exit 1
}
if (-not $secrets['CREDENTIALS_SECRET_KEY']) {
    Write-Error 'CREDENTIALS_SECRET_KEY missing.'
    exit 1
}

[Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $secrets['OPENAI_API_KEY'], 'Process')
[Environment]::SetEnvironmentVariable('CREDENTIALS_SECRET_KEY', $secrets['CREDENTIALS_SECRET_KEY'], 'Process')
if ($secrets['RUNTIME_CREDENTIALS_KEY']) {
    [Environment]::SetEnvironmentVariable('RUNTIME_CREDENTIALS_KEY', $secrets['RUNTIME_CREDENTIALS_KEY'], 'Process')
}

if ($ForceResetCredentials) {
    Remove-Item "$installerDir\config\runtime_credentials.json" -ErrorAction SilentlyContinue
    Remove-Item "$installerDir\config\.credentials_secret.key" -ErrorAction SilentlyContinue
}

Write-Host 'Starting TranscribeFlow GUI...'
Start-Process -FilePath "$installerDir\TranscribeFlow.exe" -WorkingDirectory $installerDir

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "TranscribeFlow GUI.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
$shortcut.WorkingDirectory = $scriptRoot
$shortcut.Save()
