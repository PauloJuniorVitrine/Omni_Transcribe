# Frontend Endpoint Usage — EXEC_ID 20251113T103533Z_MSJTU6

| Método | Rota | Consumo frontend | Arquivo/trecho | Status | Observações |
|--------|------|------------------|----------------|--------|-------------|
| GET | / | Lista jobs exibidos no dashboard | src/interfaces/web/templates/jobs.html (loop) | ✅ Em uso | Página inicial carrega jobs de JobController |
| GET | /jobs/{id} | Detalhe + preview e formulário | job_detail.html (contexto job/artifacts) | ✅ Em uso | Mostra artefatos e formulário de revisão |
| POST | /jobs/{id}/review | Formulário de revisão humana | job_detail.html (form) | ✅ Em uso | Envia campos reviewer/notes/decision |
| GET | /artifacts?path=... | Links de download | job_detail.html (lista artefatos) | ✅ Em uso | Abre arquivos TXT/SRT/ZIP em nova aba |
| GET | /auth/login | Não exposto em templates | — | ❌ Não referenciado | Fluxo OAuth manual (URL externa) |
| GET | /auth/callback | Não exposto em templates | — | ❌ Não referenciado | Utilizado apenas pelo provedor OAuth |
| POST | /webhooks/external | Não há consumo frontend | — | ❌ Não aplicável | Endpoint de ingestão externa |
| POST | /api/jobs/{id}/process | Não há gatilho na UI atual | — | ❌ Não referenciado | Recurso para automações/API |
