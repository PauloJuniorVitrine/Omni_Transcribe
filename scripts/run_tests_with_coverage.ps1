Param(
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"

function Invoke-PyTestWithCoverage {
    param(
        [string]$Name,
        [string]$TestPath,
        [switch]$Append
    )
    $appendFlag = ""
    if ($Append.IsPresent) {
        $appendFlag = "--cov-append"
    }
    $artifactDir = Join-Path "artifacts" $Name
    New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
    if ($appendFlag) {
        python -m pytest $TestPath `
            --cov=src `
            --cov-append `
            --cov-report=xml:$artifactDir/coverage.xml `
            --cov-report=html:$artifactDir/htmlcov `
            --cov-report=term-missing `
            --junitxml=$artifactDir/pytest-$Name.xml
    }
    else {
        python -m pytest $TestPath `
            --cov=src `
            --cov-report=xml:$artifactDir/coverage.xml `
            --cov-report=html:$artifactDir/htmlcov `
            --cov-report=term-missing `
            --junitxml=$artifactDir/pytest-$Name.xml
    }
}

Write-Host "==> Running unit tests with coverage" -ForegroundColor Cyan
$env:TEST_MODE = "1"
$env:SKIP_RUNTIME_CREDENTIALS_VERIFY = "1"
Remove-Item ".\config\runtime_credentials.json" -ErrorAction SilentlyContinue
Remove-Item ".\config\.credentials_secret.key" -ErrorAction SilentlyContinue
Invoke-PyTestWithCoverage -Name "unit" -TestPath "tests/unit"

Write-Host "==> Running integration tests with coverage (append)" -ForegroundColor Cyan
Invoke-PyTestWithCoverage -Name "integration" -TestPath "tests/integration" -Append

Write-Host "==> Running performance tests with coverage (append)" -ForegroundColor Cyan
Invoke-PyTestWithCoverage -Name "load" -TestPath "tests/performance" -Append

if (-not $SkipFrontend) {
    Write-Host "==> Running frontend JS tests with coverage" -ForegroundColor Cyan
    npm run test:js -- --coverage
}

Write-Host "Coverage reports saved under artifacts/*" -ForegroundColor Green
