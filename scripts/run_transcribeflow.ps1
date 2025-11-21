param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..")
$launcher = Join-Path $repoRoot "launcher_gui.py"

if (-not (Test-Path $launcher)) {
    Write-Error "launcher_gui.py nuo encontrado em $launcher"
    exit 1
}

if (-not $env:CREDENTIALS_SECRET_KEY) {
    Write-Error "CREDENTIALS_SECRET_KEY nuo esto definida. Defina antes de executar a GUI."
    exit 1
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python nuo encontrado no PATH."
    exit 1
}

$argsList = @($launcher, "--host", $Host, "--port", $Port)
if ($NoBrowser) { $argsList += "--no-browser" }

Write-Host "Usando CREDENTIALS_SECRET_KEY=$($env:CREDENTIALS_SECRET_KEY.Substring(0,6))******" -ForegroundColor Green
& $python.Source $argsList
