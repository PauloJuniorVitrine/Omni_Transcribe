#!/usr/bin/env bash
set -euo pipefail

if ! command -v python &> /dev/null; then
  echo "Python nao esta disponivel no PATH." >&2
  exit 1
fi

python -m pip install --upgrade pip wheel

if [ "${WHISPER_GPU:-0}" != "0" ]; then
  echo "Instalando PyTorch com suporte GPU (cu118)..."
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
  echo "Instalando PyTorch CPU..."
  pip install torch torchvision torchaudio
fi

echo "Instalando dependencias do projeto..."
pip install -r requirements.txt

echo "Ambiente local do Whisper configurado. Use ASR_ENGINE=local ao iniciar o servico."
