# UI Coverage Validation — EXEC_ID 20251113T103533Z_MSJTU6

| Ação / Endpoint | Status | Feedback Visual | Observações |
|-----------------|--------|-----------------|-------------|
| Listar jobs (GET /) | ✅ Coberto | Tabela + estado vazio | Exibe ID, arquivo, perfil, status, idioma |
| Detalhar job (GET /jobs/{id}) | ✅ Coberto | Meta list + preview | Mostra metadados e transcript |
| Aprovar/Ajustar job (POST /jobs/{id}/review) | ✅ Coberto | Flash eview-* | Não há validação client-side dos campos |
| Iniciar processamento (POST /jobs/{id}/process) | ✅ Coberto | Flash process-* | Sem spinner; pipeline roda em background |
| Download de artefatos (GET /artifacts) | ⚠️ Parcial | Flash download-error em HTML | Não há expansão de mensagens para JSON |
| Login OAuth (/auth/login/browser, /auth/callback) | ⚠️ Parcial | Flash login-success | Não há botão de logout, nem feedback para erros do provedor |
| API reprocess (/api/jobs/{id}/process) | ❌ Ausente | — | Endpoint exposto mas sem botão público (apenas UI interna cobre) |
| Webhooks externos | ❌ Não aplicável | — | Não há representação visual (apenas server-to-server) |

Resumo: UI cobre rotinas humanas (lista, detalhe, review, reprocessamento, download). Faltam elementos para logout, estado de carregamento durante processamento e UX para endpoints técnicos (API/webhook).
