# Dev Guide - TranscribeFlow

## Setup rapido
1. Python 3.11, Node 20
2. `python -m venv .venv && .\.venv\Scripts\activate` (ou `source .venv/bin/activate`)
3. `pip install -r requirements.txt`
4. `npm ci` (para testes frontend)
5. Gerar cofre se preciso: `CREDENTIALS_SECRET_KEY=<32b_urlsafe> python scripts/generate_runtime_credentials.py`
   - Dependência relevante: `PyYAML` já está no `requirements.txt` e é usada para ler perfis/templates.

## Rodando
- GUI web: `python launcher_gui.py --host 127.0.0.1 --port 8000`
  - Scripts Windows: `scripts\run_with_gui.ps1` ou `scripts\run_transcribeflow.ps1/.bat`
- GUI cobre: upload de audio (cria job + opcional processar), dashboard/filtros, incidentes, revisao, download de artefatos (token), flags, templates, credenciais.
- Watcher de audios: `python scripts/watch_inbox.py`
- CLI manual: `python -m interfaces.cli.run_job --file inbox/sample.wav --profile geral`

## Credenciais e TEST_MODE
- Em producao: `RuntimeCredentialStore` exige `CREDENTIALS_SECRET_KEY`/`RUNTIME_CREDENTIALS_KEY` e descriptografa `config/runtime_credentials.json`.
- Em testes/CI: `TEST_MODE=1` (setado em `tests/conftest.py` e nos workflows) evita tocar no cofre e usa credenciais em memoria. Se um teste precisar do fluxo real, defina `TEST_MODE=0` no escopo do teste.
- Nao comitar `config/runtime_credentials.json` real nem chaves; use `scripts/install.env.example` como referencia.

## Variaveis importantes
- `CREDENTIALS_SECRET_KEY` (obrigatoria para runtime_credentials)
- `OPENAI_API_KEY` (usada por Whisper/ChatGPT)
- `RUNTIME_CREDENTIALS_KEY` (compatibilidade com cofre)
- Pastas: BASE_INPUT_DIR, BASE_OUTPUT_DIR, BASE_PROCESSING_DIR, BASE_BACKUP_DIR, BASE_REJECTED_DIR, CSV_LOG_PATH
- Limites/chunking: MAX_AUDIO_SIZE_MB, MAX_REQUEST_BODY_MB, OPENAI_CHUNK_TRIGGER_MB, OPENAI_CHUNK_DURATION_SEC
- Outros: ACCURACY_THRESHOLD, SESSION_TTL_MINUTES, ALLOWED_DOWNLOAD_EXTENSIONS
- CORS: CORS_ALLOWED_ORIGINS (lista), CORS_ALLOW_CREDENTIALS (bool), CORS_ALLOWED_METHODS, CORS_ALLOWED_HEADERS. Em produção, use origens explícitas; por padrão aceita todos.
  - Guard: se `APP_ENV=production` e `CORS_ALLOWED_ORIGINS` contém `*`, a app falha no start.

## Testes
- Unit/integracao: `pytest`
- Frontend (Jest): `npm run test:js`
- E2E (Playwright): `npm run test:e2e` (requer `npx playwright install --with-deps`)
- Lint JS: `npm run lint:js`
- Carga leve (sugestao): marque testes com `-m load` caso adicione cenarios de paralelismo de jobs.
- Contratos/tipos: `npm run typecheck:contracts` gera OpenAPI + cliente TS e valida tipos usados pelo frontend.

## Build opcional (.exe)
- Exemplo de bundle: `pyinstaller --onefile --name TranscribeFlow launcher_gui.py`
- Garanta que `launcher_gui.py` inclui bootstrap dos caminhos (`src/`) e que as variaveis de ambiente estao definidas antes de executar o binario.

## Observacoes
- Armazenamento padrao usa arquivos JSON + filelock em `processing/`.
- Downloads exigem assinatura HMAC por padrao (flag configurable em feature flags).
- Evite commitar `config/runtime_credentials.json` ou chaves reais. 

## Smoke tests (antes de build/installer)
- Leve (stub, sem chamadas externas): `python scripts/smoke_pipeline_stub.py` valida wiring do pipeline com stubs e gera artefatos em diretorio temporario.
- Real (backend rodando): subir app (`launcher_gui.py`), realizar upload pequeno, acionar processar e baixar artefato com token; requer credenciais validas e disponibilidade do engine (OpenAI/local). Use flash/CSRF da UI ou chamadas API autenticadas.

## Persistencia (roadmap)
- Atual: JSON+filelock em `processing/`.
- Proximo passo sugerido: piloto com SQLite como backend para jobs/logs/reviews, mantendo filelock como fallback para ambientes simples. Avaliar impacto em concorrencia e migração de dados (export/import dos JSON).
## Notas de seguranca e readiness
- Downloads: `downloads.signature_required` permanece ativo por padrao; mantenha `config/feature_flags.json` integro ou defina flag explicitamente. Tokens invalidos bloqueiam download.
- Uploads: nomes de arquivos sao sanitizados (slug ASCII) e extensoes limitadas a audio permitido; respeita `MAX_AUDIO_SIZE_MB`.
- Smoke pre-release recomendado: executar upload -> process -> download (token assinado) contra backend real antes de build/installer.
