Param(
    [string]$SourceExe = "dist\TranscribeFlow.exe",
    [string]$Destination = "$env:USERPROFILE\Downloads\transcribeflow-installer"
)

if (-not (Test-Path $SourceExe)) {
    Write-Error "Source executable not found: $SourceExe"
    exit 1
}

$destDir = Resolve-Path -Path $Destination -ErrorAction SilentlyContinue
if ($destDir) {
    Remove-Item -Path $destDir -Recurse -Force
}
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
Copy-Item -Path $SourceExe -Destination "$Destination\TranscribeFlow.exe" -Force
Write-Host "Installer staged at $Destination"
