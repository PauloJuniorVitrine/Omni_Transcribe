# Test Playbook

- **Pytest (unit/integration/performance)**  
  Prompt: `pytest`  
  Ações: executa toda a suíte (unit, integração, performance) com 28 cenários; esperar resultado em ~3s.

- **Performance isolado**  
  Prompt: `pytest tests/performance -k pipeline`  
  Objetivo: medir tempo médio do pipeline end-to-end com stubs reais (`max 0.25s`).  
  Métrica: falha se média >= 0.25s.

- **HTTP throughput**  
  Prompt: `pytest tests/performance -k http`  
  Objetivo: validar latência média das rotas FastAPI ( <= 20ms por request ) usando `TestClient`.

- **Watcher smoke**  
  Prompt: `pytest tests/integration/test_watcher.py -k smoke`  
  Objetivo: garantir que eventos no `inbox/` disparam todo o pipeline (artefatos, status, logs).

- **Pipeline failure coverage**  
  Prompt: `pytest tests/integration/test_pipeline_and_review.py -k fail`  
  Objetivo: validar logging em `rejected/` para falhas em ASR e geração de artefatos.
