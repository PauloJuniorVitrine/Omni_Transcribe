# Configurando o whisper local (faster-whisper)

Para usar a melhor versão local do Whisper (`ASR_ENGINE=local`), siga estes passos:

1. **Escolha a engine local**  
   Defina `ASR_ENGINE=local` no `.env` (ou no ambiente) antes de iniciar o serviço.

2. **Instale as dependências pesadas**  
   Use os scripts:
   ```bash
   scripts/setup_local_whisper_env.sh         # Linux/macOS
   .\\scripts\\setup_local_whisper_env.ps1    # Windows PowerShell
   ```
   Eles instalam `torch`, `torchaudio`, `faster-whisper` e os pacotes do `requirements.txt`. Passe `WHISPER_GPU=1` (Linux/macOS) ou `-Gpu` (PowerShell) para baixar a variante com CUDA.

3. **Valide a instalação**  
   ```bash
   python - <<'PY'
   from faster_whisper import WhisperModel
   model = WhisperModel("large", device="cpu")
   segments, info = model.transcribe("examples/sample.wav")
   print("Idioma detectado:", info.language)
   PY
   ```
   Confirme que `torch.cuda.is_available()` retorna `True` se estiver usando GPU.

4. **Diretório src no sys.path (PyInstaller)**  
   O `scripts/run_job.py` já ajusta `sys.path` para garantir que o `src/` seja encontrado dentro do `.exe`.
   Quando você rebuildar manualmente, use:
   ```bash
   pyinstaller src/interfaces/cli/run_job.py --name TranscribeFlow --onefile --noconfirm --paths src
   ```

5. **Execute testes ou o watcher**  
   ```bash
   python -m tests.integration.test_pipeline_and_review
   python -m src.interfaces.cli.watch_inbox
   ```
   O container reutiliza o mesmo pipeline com o `TranscriptionAccuracyGuard`.
