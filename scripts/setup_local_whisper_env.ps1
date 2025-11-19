param(
    [switch]$Gpu
)

Write-Host "Updating pip..."
python -m pip install --upgrade pip wheel

if ($Gpu.IsPresent) {
    Write-Host "Installing GPU-accelerated PyTorch (cu118)..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
}
else {
    Write-Host "Installing CPU-only PyTorch..."
    pip install torch torchvision torchaudio
}

Write-Host "Installing project dependencies..."
pip install -r requirements.txt

Write-Host "Local Whisper environment is ready. Set ASR_ENGINE=local before starting the service."
