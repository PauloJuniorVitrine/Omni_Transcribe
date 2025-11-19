# FEEDBACK & LEARN — EXEC_ID 20251113T103533Z_MSJTU6

- Adoção precoce do container de serviços facilitou a injeção de dependências, mas exigiu planejamento para etapas posteriores (ex.: ArtifactBuilder). Em futuras execuções, considerar stubs para antecipar requisitos sem bloquear etapas.
- O repositório em arquivos JSON atende ao MVP, porém deve ser substituído por banco relacional ou cache distribuído antes de escala; prever migração incremental.
- O watcher precisa de testes de carga para validar concorrência quando múltiplos áudios chegam simultaneamente. Sugestão: fila intermediária (Celery/Redis) em iteração futura.
