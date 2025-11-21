# Estrutura de testes

- Unit: `tests/unit/` (coletado por padrao)
- Integracao: `tests/integration/` (nome de arquivos `test_*.py`; coberto via `pytest.ini` e `pytest tests/integration`)
- Performance: `tests/performance/` (executado via job load da CI)

# Descoberta do pytest
- `pytest.ini` define `testpaths` incluindo unit, integration e performance.
- Convencoes padrao: arquivos `test_*.py`, classes `Test*`, funcoes `test_*`.
- Markers registrados: `integration`, `performance` (para uso futuro/filtragem).

# Test mode / credenciais
- `tests/conftest.py` seta `TEST_MODE=1` para evitar decrypt de credenciais em ambientes de teste/CI.
- Se algum teste precisar forcar fluxo real de criptografia, defina `TEST_MODE=0` no escopo do teste.
