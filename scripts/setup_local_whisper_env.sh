#!/usr/bin/env bash
set -euo pipefail

# Ensure pip and wheel are available before installing heavy dependencies
python -m pip install --upgrade pip wheel

# Optional GPU support: set WHISPER_GPU=1 and optionally TORCH_CUDA_ARCH_LIST before running the script.
if [ "${WHISPER_GPU:-0}" != "0" ]; then
  echo "Installing GPU-accelerated PyTorch (cu118)..."
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
  echo "Installing CPU-only PyTorch..."
  pip install torch torchvision torchaudio
fi

echo "Installing project dependencies..."
pip install -r requirements.txt

echo "Local Whisper environment is ready. Set ASR_ENGINE=local before starting the service."
