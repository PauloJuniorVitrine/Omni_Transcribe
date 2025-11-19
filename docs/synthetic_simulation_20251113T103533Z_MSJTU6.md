# Synthetic Simulation – EXEC_ID 20251113T103533Z_MSJTU6

## Cenário simulado
- **Entrada:** job fictício `job-sim-001` com áudio 6h em português, profile `podcast-br`.  
- **Fluxo:** watcher cria job → pipeline ASR (`faster-whisper`/OpenAI) → pós-edição ChatGPT → geração de artefatos e logs.

## Observações
1. **Tempo de execução estimado:** ~45 min (chunking automático `OPENAI_CHUNK_DURATION_SEC=900`).  
2. **Logs esperados:** eventos `process_started`, `chunk_upload`, `post_edit_complete`, `artifact_saved`.  
3. **Reação da UI:** dashboard mostra incremento de “Aguardando revisão”; incidents devem permanecer vazios se tudo OK.  
4. **Potenciais gargalos:** limite de 200 MB (`max_request_body_mb`), necessidade de streaming para jobs longos.  

## Próximas ações
- Automatizar esse cenário com dados mockados (fixtures em `tests/performance/` ou scripts de load) e registrar resultados em `docs/synthetic_simulation_{EXEC_ID}.md` ao final de cada release.
