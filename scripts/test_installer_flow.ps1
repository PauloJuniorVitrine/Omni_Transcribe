Param(
    [string]$EnvFile = ".\scripts\install.env",
    [int]$StartupTimeout = 60
)

function Import-EnvFile {
    param ($Path)
    if (-not (Test-Path $Path)) {
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

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFilePath = Resolve-Path $EnvFile -ErrorAction SilentlyContinue
if (-not $envFilePath) {
    Write-Error "Arquivo de ambiente não encontrado: $EnvFile"
    exit 1
}

$envVars = Import-EnvFile -Path $envFilePath
if (-not $envVars['OPENAI_API_KEY'] -or -not $envVars['CREDENTIALS_SECRET_KEY']) {
    Write-Error "OPENAI_API_KEY e CREDENTIALS_SECRET_KEY precisam estar definidos em $envFilePath"
    exit 1
}

$env:OPENAI_API_KEY = $envVars['OPENAI_API_KEY']
$env:CREDENTIALS_SECRET_KEY = $envVars['CREDENTIALS_SECRET_KEY']
if ($envVars['RUNTIME_CREDENTIALS_KEY']) {
    $env:RUNTIME_CREDENTIALS_KEY = $envVars['RUNTIME_CREDENTIALS_KEY']
}

$runScript = Join-Path $scriptDirectory "run_with_gui.ps1"
if (-not (Test-Path $runScript)) {
    Write-Error "Script run_with_gui.ps1 ausente em $scriptDirectory"
    exit 1
}

$installerLog = Join-Path $scriptDirectory "installer_test.log"
Remove-Item $installerLog -ErrorAction SilentlyContinue

$runArgs = "-ExecutionPolicy Bypass -File `"$runScript`" -ForceResetCredentials"
$runner = Start-Process -FilePath "powershell.exe" -ArgumentList $runArgs -NoNewWindow -PassThru

Write-Host "Aguardando TranscribeFlow subir..."
$elapsed = 0
do {
    Start-Sleep -Seconds 5
    $elapsed += 5
    $server = Get-Process -Name TranscribeFlow -ErrorAction SilentlyContinue
    if ($server) {
        break
    }
} until ($elapsed -ge $StartupTimeout)

if (-not $server) {
    Write-Error "TranscribeFlow não iniciou dentro de $StartupTimeout segundos."
    Stop-Process -Id $runner.Id -ErrorAction SilentlyContinue
    exit 1
}

$requestUrl = "http://localhost:8000"
$response = $null
try {
    $response = Invoke-WebRequest -Uri $requestUrl -UseBasicParsing -TimeoutSec 5
} catch {
    Write-Error "Não foi possível alcançar $requestUrl: $_"
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
    exit 1
}

if ($response.StatusCode -ne 200) {
    Write-Error "Endpoint retornou status $($response.StatusCode)"
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "Validação concluída: TranscribeFlow respondeu em $requestUrl."
Stop-Process -Id $server.Id
Stop-Process -Id $runner.Id

Write-Host "Suite do instalador executada com sucesso."
