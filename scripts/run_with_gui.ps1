Param(
    [switch]$ForceResetCredentials,
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoBrowser
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
$repoRoot = Resolve-Path (Join-Path $scriptRoot '..')
$envFiles = @(
    Join-Path $scriptRoot 'install.local.env',
    Join-Path $scriptRoot 'install.env',
    Join-Path $repoRoot '.env'
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
    Write-Error 'OPENAI_API_KEY missing in env file or environment.'
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
    Remove-Item "$repoRoot\config\runtime_credentials.json" -ErrorAction SilentlyContinue
    Remove-Item "$repoRoot\config\.credentials_secret.key" -ErrorAction SilentlyContinue
}

$launcher = Join-Path $repoRoot 'launcher_gui.py'
if (-not (Test-Path $launcher)) {
    Write-Error "launcher_gui.py not found at $launcher"
    exit 1
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python not found in PATH."
    exit 1
}

$argsList = @($launcher, "--host", $Host, "--port", $Port)
if ($NoBrowser) { $argsList += "--no-browser" }

Write-Host "Starting TranscribeFlow GUI via Python..." -ForegroundColor Green
Start-Process -FilePath $python.Source -ArgumentList $argsList -WorkingDirectory $repoRoot

# Create/refresh desktop shortcut pointing to this script for convenience.
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "TranscribeFlow GUI.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
$shortcut.WorkingDirectory = $scriptRoot
$shortcut.Save()
