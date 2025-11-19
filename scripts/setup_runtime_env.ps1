param(
    [Parameter(Mandatory=$false)]
    [string]$Secret
)

function Get-RuntimeSecret {
    param([string]$EnvValue, [string]$Provided)
    if ($Provided) { return $Provided }
    if ($EnvValue) { return $EnvValue }
    return $null
}

$runtimeSecret = Get-RuntimeSecret -EnvValue $env:CREDENTIALS_SECRET_KEY -Provided $Secret

if (-not $runtimeSecret) {
    Write-Host "Gerando nova chave CREDENTIALS_SECRET_KEY..." -ForegroundColor Yellow
    $runtimeSecret = python - <<'PY'
import secrets, base64
print(base64.urlsafe_b64encode(secrets.token_bytes(24)).decode('utf-8'))
PY
}

$env:CREDENTIALS_SECRET_KEY = $runtimeSecret
Write-Host "CREDENTIALS_SECRET_KEY definido: $($runtimeSecret.Substring(0,6))..." -ForegroundColor Green

Write-Host "Atualizando cofre runtime..." -ForegroundColor Cyan
python scripts/generate_runtime_credentials.py

Write-Host "Executando pytest tests/unit -q..." -ForegroundColor Cyan
pytest tests/unit -q
