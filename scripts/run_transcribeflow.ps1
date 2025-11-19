param(
    [string]$Executable = ".\\TranscribeFlow.exe"
)

if (-not $env:CREDENTIALS_SECRET_KEY) {
    Write-Error "CREDENTIALS_SECRET_KEY não está definida. Defina antes de executar o binário."
    exit 1
}

Write-Host "Usando CREDENTIALS_SECRET_KEY={$env:CREDENTIALS_SECRET_KEY.Substring(0,6)}…" -ForegroundColor Green
& $Executable @args
