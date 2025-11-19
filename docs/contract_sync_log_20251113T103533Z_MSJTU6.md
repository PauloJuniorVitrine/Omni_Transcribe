# Contract Sync Log — EXEC_ID 20251113T103533Z_MSJTU6

| Endpoint | Método | Contrato backend | Consumo frontend | Status | Observações |
|----------|--------|------------------|------------------|--------|-------------|
| / (jobs) | GET | Retorna HTML com contexto jobs | Template jobs.html requer jobs iterable com campos id/status/language | ✅ Sincronizado | Nenhum campo ausente; fallback template cobre lista vazia |
| /jobs/{id} | GET | Contexto job, rtifacts, 	ranscript_preview | Template job_detail.html usa esses campos | ✅ Sincronizado | Apenas nota: mensagens 404 não renderizadas na UI |
| /jobs/{id}/review | POST | Form data reviewer/decision/notes → redirect | Form no template envia exatamente esses campos | ✅ Sincronizado | Não há feedback de erro ao usuário (poderia exibir flash) |
| /artifacts | GET | Query param path validado + FileResponse | Links de download usam caminho absoluto expandido | ⚠️ Parcial | Template assume que caminhos já são confiáveis; nenhum slug amigável |
| /api/jobs/{id}/process | POST | JSON {job_id,status} ou erro 400 | Não consumido no frontend | ⚠️ Parcial | Endpoint exposto sem UI; documentar para uso API |
| /auth/login | GET | JSON {url,state} | Frontend não utiliza | ⚠️ Parcial | Fluxo manual; UI não redireciona automaticamente |
| /auth/callback | GET | Define cookie + JSON tokens | Frontend não consome resposta JSON | ⚠️ Parcial | Considerar redirect amigável pós-login |
| /webhooks/external | POST | Valida assinatura e retorna JSON (status, trace) | Não há consumo frontend | ✅ Sincronizado | Destinado a integrações externas |
