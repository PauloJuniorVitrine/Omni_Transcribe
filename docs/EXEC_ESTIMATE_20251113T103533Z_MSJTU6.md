# TranscribeFlow – Execution Estimate

- EXEC_ID: 20251113T103533Z_MSJTU6
- Generated (UTC): 2025-11-13T10:35:33Z
- Methodology: Sequential blocks; no parallelization per prompt; buffers already include contingency for refactors/logging.

| Bloco | Conteúdo Principal | Estimativa (h) |
| --- | --- | --- |
| 1. Governança & Diretórios | EXEC_ID, estimativas, scaffolding inicial de documentação/logs | 1.0 |
| 2. Configuração Base | `.env`, carregador de perfis, `Settings`, estrutura de pastas físicas (`src`, `inbox`, `output`, etc.) | 2.0 |
| 3. Domínio | Entidades, value objects, contratos das portas/repositórios | 2.5 |
| 4. Casos de Uso | Pipeline completo (jobs, pós-edição, artefatos, revisão, fallback) | 5.0 |
| 5. Serviços de Aplicação | Serviços ASR, GPT, gerador de artefatos, logger/planilha, retry/backoff | 4.0 |
| 6. Infraestrutura | Adapters OpenAI/faster-whisper, storage local, CSV repositories, packaging | 4.0 |
| 7. Interfaces | FastAPI + UI Jinja, CLI watcher/scripts | 4.5 |
| 8. Artefatos & Backup | TXT/SRT/VTT/JSON builders, ZIP, registro em `output/log.csv`, rejected handling | 3.5 |
| 9. Documentação & Logs | `REVIEW_LOG.md`, `CHANGE_SUMMARY.md`, erros, feedback | 1.5 |
| 10. Validação Manual | Smoke scripts, checklist final, ajustes pós-review | 1.0 |

**Total estimado:** 29.0 horas de execução contínua.

## Dependências e Premissas
- Credenciais OpenAI/Redis/GoTranscript/S3 serão mockadas quando não disponíveis.
- CSV/JSON atuam como persistência principal nesta iteração, com interfaces prontas para migração.
- Nenhuma automação externa (upload GoTranscript, Sheets API) será acionada sem credenciais; adapters permanecem prontos.

## Riscos Principais
1. Complexidade no formatter de legendas obedecendo parâmetros dinâmicos por perfil.
2. Conectores OpenAI/faster-whisper exigem tratamento cuidadoso para tempos de resposta e retentativas.
3. Gestão de versões (`v1`, `v2`, …) e rastreabilidade integral pode aumentar overhead operacional.

Mitigações: testes unitários direcionados para formatters/parsers, camadas de abstração claras, e scripts de validação para checar consistência de diretórios/logs antes de finalizar.
