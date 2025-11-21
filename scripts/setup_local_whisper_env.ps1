param(
    [switch]$Gpu
)

Write-Host "Atualizando pip..."
python -m pip install --upgrade pip wheel

if ($Gpu.IsPresent) {
    Write-Host "Instalando PyTorch com suporte GPU (cu118)..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
}
else {
    Write-Host "Instalando PyTorch CPU..."
    pip install torch torchvision torchaudio
}

Write-Host "Instalando dependencias do projeto..."
pip install -r requirements.txt

Write-Host "Ambiente local mais robusto para 'faster-whisper' pronto. Inicie o servico com ASR_ENGINE=local."
