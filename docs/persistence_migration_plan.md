# Plano de migracao de persistencia (JSON/filelock -> SQLite/Postgres)

## Motivacao
- File-based (JSON + filelock) e simples, mas sensivel a corrupcao e concorrencia alta.
- Necessidade de queries mais ricas (logs, jobs) e escalabilidade moderada.

## Objetivo
- Introduzir backend SQLite opcional (fallback para JSON) com caminho de migracao reversivel.
- Possivel passo futuro: Postgres em producao.

## Proposta tecnica
1) Adicionar setting `PERSISTENCE_BACKEND` (`file`, `sqlite`) e `DATABASE_URL` para SQLite (ex.: `sqlite:///processing/transcribeflow.db`).
2) Criar camada de repositórios que implementem a mesma interface atual:
   - `SqlJobRepository`, `SqlArtifactRepository`, `SqlLogRepository`, `SqlReviewRepository`.
   - Usar SQLAlchemy ou raw SQL simples; migracoes com Alembic se adotar Postgres depois.
3) Container (`infrastructure/container/components_storage.py`) seleciona implementação conforme setting.
4) Migração de dados:
   - Script `scripts/migrate_file_to_sqlite.py` que lê JSON existente e popula SQLite.
   - Backup dos JSON antes de migrar.
5) Backward compatibility:
   - Manter repositórios filelock para ambientes simples/testes.
   - Flag clara para rollback: basta apontar para backend `file` e usar backups.

## Passos sugeridos
- Sprint 1: implementar repositórios SQLite + flag, sem remover JSON; adicionar testes de integração para ambos.
- Sprint 2: script de migração, smoke com SQLite, medir concorrência (pytests/performance).
- Sprint 3: opcional Postgres (ajustar `DATABASE_URL`, migrations, helm/infra).

## Consideracoes
- Tracing/observabilidade: manter trace_id/logs em repositórios; garantir transacoes atomicamente.
- Locks: SQLite lida melhor com concorrencia leve; Postgres para alta concorrencia.
- Backup/restore: adicionar tarefa de cron para dump SQLite ou snapshots de volume.
