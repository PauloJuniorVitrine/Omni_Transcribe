# Executando a “melhor versão” local do Whisper

Este projeto já suporta o engine local (`EngineType.LOCAL`) e a arquitetura não depende da OpenAI quando `ASR_ENGINE=local`. Para garantir que o pipeline use o **faster-whisper**/PyTorch mais comprensivo, siga estes passos:

1. **Configure o ambiente**
   - Defina `ASR_ENGINE=local` no `.env` ou no sistema para que o `ServiceContainer` construa o cliente `FasterWhisperClient`.
   - Opcional: ajuste `LOCAL_WHISPER_MODEL_SIZE` (ex.: `large` ou `xlarge`) e `MAX_AUDIO_SIZE_MB` se estiver processando longos minutos.

2. **Instale as dependências pesadas**
   - Há dois scripts auxiliares em `scripts/`:
     - `scripts/setup_local_whisper_env.sh` (Linux/macOS)
     - `scripts/setup_local_whisper_env.ps1` (Windows PowerShell)
   - Execute o script correspondente _antes_ de iniciar a aplicação. Passe `WHISPER_GPU=1` (Linux) ou `-Gpu` (PowerShell) para instalar a variante GPU do PyTorch; caso contrário, será instalada a versão CPU.

3. **Verifique o setup**
   - Rode `python -c "import whisper; print('faster-whisper', whisper.__version__)"` para confirmar que o pacote e seus binários foram carregados.
   - Teste a inferência local com um áudio curto:
     ```bash
     python - <<'PY'
     from faster_whisper import WhisperModel
     model = WhisperModel("large", device="cpu")
     segments, info = model.transcribe("examples/sample.wav")
     print("Idioma detectado:", info.language)
     PY
     ```
   - Se usar GPU, confirme que `torch.cuda.is_available()` retorna `True`.

4. **Considere variáveis de ambiente extras (GPU)**
   - `TORCH_CUDA_ARCH_LIST` pode ser necessária em ambientes com GPUs customizadas.
   - `WHISPER_TEMP_DIR` (nome fictício) não existe no repo, mas você pode exportar `TMPDIR` para controlar onde os chunkings temporários são salvos.

5. **Execute o sistema**
   - Inicie o watcher (`python -m src.interfaces.cli.watch_inbox`) ou o servidor HTTP (`uvicorn src.interfaces.http.app:app`) normalmente. O `WhisperService` já escolhe chunking e fallback se detectar arquivos grandes.

O workflow `system-validation.yml` já instala estas dependências mediante `pip install -r requirements.txt`, mas o script acima garante que o `torch` correto esteja presente quando você estiver em uma máquina com GPU. Use essas etapas antes de executar testes locais/manuais com o `ASR_ENGINE=local`.
