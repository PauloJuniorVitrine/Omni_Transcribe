Param(
    [string]$EnvFile = 'scripts/install.env',
    [int]$StartupTimeout = 60
)

function Import-EnvFile {
    param($Path)
    if (-not (Test-Path $Path)) { return @{} }
    $values = @{}
    foreach ($line in Get-Content $Path | Where-Object { ($_ -and -not $_.StartsWith('#')) -and ($_.Trim() -ne '') }) {
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $value = $parts[1].Trim()
            $value = $value.Trim("'")
            $value = $value.Trim('"')
            $values[$key] = $value
        }
    }
    return $values
}

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFilePath = $null
$candidateFiles = @(Join-Path $scriptDirectory 'install.local.env') + @(Join-Path $scriptDirectory 'install.env')
foreach ($candidate in $candidateFiles) {
    if (Test-Path $candidate) { $envFilePath = $candidate; break }
}

if (-not $envFilePath) {
    $envFilePath = Resolve-Path $EnvFile -ErrorAction SilentlyContinue
}

if (-not $envFilePath) {
    Write-Error ('Environment file not found. Checked install.local.env, install.env, and {0}' -f $EnvFile)
    exit 1
}

$envVars = Import-EnvFile -Path $envFilePath
if (-not $envVars['OPENAI_API_KEY'] -or -not $envVars['CREDENTIALS_SECRET_KEY']) {
    Write-Error 'OPENAI_API_KEY and CREDENTIALS_SECRET_KEY are required'
    exit 1
}

$env:OPENAI_API_KEY = $envVars['OPENAI_API_KEY']
$env:CREDENTIALS_SECRET_KEY = $envVars['CREDENTIALS_SECRET_KEY']
if ($envVars['RUNTIME_CREDENTIALS_KEY']) { $env:RUNTIME_CREDENTIALS_KEY = $envVars['RUNTIME_CREDENTIALS_KEY'] }

$runScript = Join-Path $scriptDirectory 'run_with_gui.ps1'
if (-not (Test-Path $runScript)) { Write-Error 'run_with_gui.ps1 not found'; exit 1 }

$installerDirectory = Join-Path $scriptDirectory '..\..\Downloads\transcribeflow-installer'
$installerDirectory = Resolve-Path $installerDirectory -ErrorAction SilentlyContinue
if (-not $installerDirectory) { Write-Error 'Installer directory not found. Expected ..\..\Downloads\transcribeflow-installer'; exit 1 }
$installerDirectory = $installerDirectory.Path

$logFile = Join-Path $scriptDirectory 'installer_test.log'
Remove-Item $logFile -ErrorAction SilentlyContinue

$runner = Start-Process -FilePath 'powershell.exe' -ArgumentList '-ExecutionPolicy','Bypass','-File',$runScript,'-ForceResetCredentials' -NoNewWindow -PassThru

Write-Host 'Waiting for TranscribeFlow to start...'
$elapsed = 0
$server = $null
while ($elapsed -lt $StartupTimeout) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    $server = Get-Process -Name TranscribeFlow -ErrorAction SilentlyContinue
    if ($server) { break }
}

if (-not $server) {
    Write-Error ('TranscribeFlow did not start within {0} seconds.' -f $StartupTimeout)
    Stop-Process -Id $runner.Id -ErrorAction SilentlyContinue
    exit 1
}

$requestUrl = 'http://localhost:8000'
try {
    $response = Invoke-WebRequest -Uri $requestUrl -UseBasicParsing -TimeoutSec 5
} catch {
    Write-Error ('Unable to reach {0}: {1}' -f $requestUrl, $_)
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
    exit 1
}

if ($response.StatusCode -ne 200) {
    Write-Error ('Endpoint returned status {0}' -f $response.StatusCode)
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
    exit 1
}

Write-Host ('Installer suite completed. TranscribeFlow is responding at {0}.' -f $requestUrl)
Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
Stop-Process -Id $runner.Id -ErrorAction SilentlyContinue
