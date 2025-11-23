# Smoke real (upload -> process -> download token)

## Objetivo
Validar ponta a ponta em backend real (sem stubs) antes de build/installer: upload de audio, processamento completo e download assinado de artefato.

## Pre-requisitos
- Backend rodando (`python launcher_gui.py --host 127.0.0.1 --port 8000`).
- Credenciais validas configuradas (`OPENAI_API_KEY` ou engine local).
- Feature flag `downloads.signature_required` ativa (default).
- Sessao autenticada via `/auth/login` (ou definir `TEST_MODE=1` para bypass em ambiente de teste controlado).

## Passo a passo (manual)
1. Iniciar backend com env seguro (sem TEST_MODE) e CORS/CSRF configurados.
2. Abrir UI e fazer login (OAuth) ou, em teste, setar cookie de sessao usando `/auth/login`.
3. Fazer upload pequeno via UI ou curl:
   ```bash
   curl -v -b "session_id=<cookie>" -F "file=@inbox/sample.wav" -F "profile=geral" -F "engine=openai" http://127.0.0.1:8000/jobs/upload
   ```
4. Na UI, acionar “Processar” ou via API:
   ```bash
   curl -X POST -b "session_id=<cookie>" -H "X-CSRF-Token:<csrf>" http://127.0.0.1:8000/api/jobs/<job_id>/process
   ```
5. Aguardar status `awaiting_review` na UI ou via `/api/dashboard/summary`.
6. Ir em `/jobs/<job_id>` e baixar artefato assinado; validar que token é exigido (401 sem token).
7. Registrar resultado no checklist de deploy.

## Variacao com engine local
- Definir `ASR_ENGINE=local` e preparar modelo faster-whisper (ver docs/local_whisper_setup).

## Dica de automacao
- Incluir comando manual no pipeline (job opcional) executando upload/process/download com `TEST_MODE=0` e armazenamento isolado.
