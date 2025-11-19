# Cross Module Impact – EXEC_ID 20251113T103533Z_MSJTU6

## Resumo
- **Impacto direto:** `config/runtime_credentials.py` → `config/__init__.py` → todos os controllers (dependem do store para aplicar credenciais em tempo de execução).  
- **Impacto indireto:** Novos endpoints `/api/jobs/{id}/logs*` afetam `src/interfaces/web/templates/job_detail.html` e os módulos JS (`js/jobs.js`) que agora consomem dados assíncronos.

## Tabela
| Origem | Módulos afetados | Tipo | Observação | Mitigação |
| --- | --- | --- | --- | --- |
| `config/runtime_credentials.py` | `config/__init__.py`, watchers, FastAPI middlewares | Direto | Sem `CREDENTIALS_SECRET_KEY` em produção, leitura de payload cifrado falha. | Documentar variável obrigatória + fallback seguro em dev. |
| `/api/jobs/{id}/logs`, `_query_job_logs` | `js/jobs.js`, `job_detail.html` | Direto | UI depende de endpoint JSON, falha do backend gera toasts de erro. | Adicionar retries/observabilidade. |
| Modularização JS (`core/global/dashboard/settings`) | Todas as páginas que importam `/static/app.js` | Indireto | Browsers legados sem suporte a modules não carregarão scripts. | Registrar requisito (ES2015+) e considerar transpile opcional. |

## Mapa de Calor (texto)
- **Config/Security:** risco alto (depende de env).  
- **HTTP/API:** risco médio (novos endpoints).  
- **Frontend:** risco médio (ES modules).  
- **Watcher/Domain:** risco baixo (não tocados).
