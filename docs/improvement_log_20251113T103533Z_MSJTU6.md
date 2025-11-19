# Improvement Log – EXEC_ID 20251113T103533Z_MSJTU6

| ID | Descrição | Arquivos principais | Data/Hora (UTC) | Tamanho aprox. | Status |
| --- | --- | --- | --- | --- | --- |
| IMP-002 | Store de credenciais criptografado com auditoria (`runtime_credentials.py`), dependência `cryptography` e testes unitários. | `config/runtime_credentials.py`, `requirements.txt`, `tests/unit/config/test_runtime_credentials.py` | 2025-11-13T23:45Z | ~170 linhas | ✅ Aplicada |
| IMP-001 (parcial) | API JSON para logs (+ export), controller enxuto e testes de integração. | `src/interfaces/http/app.py`, `tests/integration/test_http_api.py` | 2025-11-13T23:55Z | ~220 linhas | ✅ Aplicada |
| IMP-003 (parcial) | Modularização do JS (`core/global/dashboard/jobs/settings`), bootstrap ES module e UI de logs via fetch + export estruturado. | `src/interfaces/web/templates/base.html`, `src/interfaces/web/templates/job_detail.html`, `src/interfaces/web/static/js/*.js`, `src/interfaces/web/static/app.js` | 2025-11-14T00:15Z | ~300 linhas | ✅ Aplicada |

### Observações
- Cada alteração foi acompanhada de `pytest -q` (49 testes) garantindo regressão nula.  
- Logs de auditoria de credenciais agora registram toda modificação em `config/runtime_credentials_audit.log`.  
- Modularização do front prepara terreno para bundlers/testes, mas depende de tooling JS (npm não disponível no ambiente atual).
