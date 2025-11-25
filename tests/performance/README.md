# Suíte de Performance do Omni Transcribe

Esta pasta concentra testes de performance dentro do pytest (`-m performance`). Os cenários cobertos hoje são:

1. **HTTP**  
   - `test_http_performance.py` monitora endpoints críticos:
     * `/` (dashboard principal) — latência alvo ≤ 50 ms.  
     * `/jobs` (lista de jobs) — latência alvo ≤ 80 ms.  
     * `/jobs/job-perf` (detalhe simplificado) — latência alvo ≤ 100 ms.  
     * `/health` (probe simples) — latência alvo ≤ 50 ms.  
   - Cada execução valida status < 500 e compara o tempo real com os thresholds definidos em `HTTP_ENDPOINTS`.

2. **Pipeline**  
   - `test_pipeline_performance.py` mede:
     * Job único (`test_pipeline_average_execution_time`) com média máxima de 0.6 s.  
     * Batch sequencial de jobs (`test_pipeline_batch_average`) com médias configuradas para 5 jobs (≤ 0.9 s) e 20 jobs (≤ 1.3 s).  
     * Concorrência controlada (`test_pipeline_concurrent_p95`) com p95 ≤ 1.4 s usando ThreadPoolExecutor.

3. **Procedimento para rodar**  
   ```bash
   pytest tests/performance -m performance -q
   ```
   Esta seleção garante que apenas os testes marcados como `@pytest.mark.performance` sejam executados.

4. **Integração com CI/CD**  
   - Recomenda-se executar esta suíte sempre que houver mudanças significativas no pipeline (ASR, chunking, templates) ou no HTTP (uploads/downloads).  
   - Para detecção de regressão, compare os tempos médios/p95 com os valores estabelecidos acima.

5. **Resultados úteis**  
   - O relatório de cobertura (`coverage.xml/htmlcov/`) também inclui os testes de performance (stats de tempo).
   - Em caso de falha, o pytest exibirá o endpoint ou cenário que ultrapassou o limite definido.
