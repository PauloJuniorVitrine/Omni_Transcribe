# Naming Inconsistencies – EXEC_ID 20251113T103533Z_MSJTU6

| Termo | Ocorrências | Problema | Proposta |
| --- | --- | --- | --- |
| `process` (verbos e rotas) | `/api/jobs/{id}/process`, `bindProcessActions`, `process_job` | Usado tanto para reprocessar quanto para pipelines distintos. | Renomear handlers/rotas para `run_pipeline` ou `restart_pipeline` para reduzir ambiguidade. |
| `logs_page` vs API `page/page_size` | Template job_detail usa query histórica (`logs_page`) enquanto nova API usa `page`. | Pode confundir ao misturar funcionalidade antiga/novas. | Migrar completamente para API JSON e renomear campos HTML para `page`. |
| `process-status` label | `data-process-status` mostra “Pipeline em execução”/“Processamento manual”. | Nome pouco específico – status se aplica apenas ao job atual. | Trocar por `data-job-process-status` para evitar colisão futura. |

## Observações
- Não foram detectados nomes duplicados entre módulos diferentes (ex.: duas classes `Manager`).  
- Recomenda-se padronizar enums/strings para português ou inglês – hoje coexistem “review-approved” e “process-started” (inglês) com textos em pt-BR.
