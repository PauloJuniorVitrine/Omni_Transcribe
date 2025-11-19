# Backend ↔ Frontend Contract — EXEC_ID 20251113T103533Z_MSJTU6

## Rotas Consumidas pela UI

| Rota | Método | Payload/Parâmetros | Resposta | Consumidor UI |
|------|--------|--------------------|----------|---------------|
| / | GET | limit opcional (query) | HTML com contexto jobs | jobs.html lista tabela |
| /jobs/{job_id} | GET | Path job_id | HTML com job, rtifacts, 	ranscript_preview, flashes | job_detail.html |
| /jobs/{job_id}/review | POST | Form eviewer, decision, 
otes | Redirect 303 /jobs/{job_id}?flash=review-* | Form em job_detail.html |
| /jobs/{job_id}/process | POST | sem corpo (botão) | Redirect 303 com flash process-* | Novo form em job_detail.html |
| /artifacts?path=&job_id= | GET | Query path obrigatória, job_id opcional | FileResponse ou redirect lash=download-error | Links de download |
| /auth/login/browser | GET | — | Redirect 302 para provedor OAuth | Link “Entrar” em ase.html |
| /auth/callback | GET | Query code (obrigatório) | JSON (Accept=JSON) ou redirect / com flash login | Pós login browser |

## Rotas API / Integrações (sem UI)

| Rota | Método | Uso previsto |
|------|--------|--------------|
| /api/jobs/{job_id}/process | POST | Automação/API chama pipeline direto |
| /auth/login | GET | Integradores podem obter URL/estado para embed |
| /webhooks/external | POST | Integrações externas (HMAC + timestamp) |

## Flashes e Estados

- eview-approved / eview-adjust → mostrados em /jobs/{id} após envio do formulário.
- process-started / process-error → feedback do botão “Iniciar processamento”.
- download-error → ativado quando /artifacts cai em fallback HTML; logs registram warning.
- login-success → exibido na home após callback sucesso.

## Notas
- Todas as rotas exigem sessão (equire_active_session) exceto /auth/* e /webhooks/external.
- Forms HTML usam POST e seguem Redirect 303 para evitar reenvio.
- Erros JSON permanecem via HTTPException; fallback para HTML redireciona com flash.

