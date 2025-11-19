# Missing Tests – EXEC_ID 20251113T103533Z_MSJTU6

| ID | Módulo/Função | Falta | Risco | Sugestão |
| --- | --- | --- | --- | --- |
| TESTMISS-001 | `js/dashboard.js`, `js/jobs.js`, `js/settings.js` | Não há lint/testes automatizados para os módulos ES introduzidos. Ambiente atual não possui npm, impossibilitando Jest/Playwright. | Médio – regressões de UI não são detectadas. | Em ambiente com Node, adicionar `package.json`, ESLint + Jest e testes básicos (polling, AJAX, modais). |
| TESTMISS-002 | `/api/jobs/{id}/logs` | Coberto por integração, mas falta teste de erro (sem job / sem permissão). | Baixo | Ampliar `tests/integration/test_http_api.py` com cenários 404/401. |

## Observação
- Enquanto não houver tooling npm instalado, registrar no pipeline (CI) para executar lint/testes JS em ambiente preparado.
