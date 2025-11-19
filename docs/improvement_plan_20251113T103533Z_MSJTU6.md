# Plano de Melhoria – EXEC_ID 20251113T103533Z_MSJTU6

## Tabela de backlog (ordenada por criticidade)
| ID | Descrição técnica | Módulo | Diretório | Gravidade | Impacto | Scope | Camada | Tags | Prioridade | Custo_estimado_horas | Risco_de_regressao | IMPACT_SCORE | Score técnico antes/depois | Relevância (logs) | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **IMP-001** | Extrair `job_detail` para um query/presenter assíncrono com endpoints JSON para logs/exportação, reduzindo IO síncrono na rota (`Linhas ≈180`, `PesoCamada=3`, `debt_ratio=0.20`). | Interfaces HTTP | `src/interfaces/http/app.py` | Alta | Alta | system | Interface/Application | @refactor @performance | Alta | 10 | Médio | **708** | 58 → 82 | Não | 🔲 Pendente |
| **IMP-002** | Criptografar `runtime_credentials.json`, versionar por ambiente e adicionar trilha de auditoria/rotação automática (`Linhas ≈120`, `PesoCamada=4`, `debt_ratio=0.35`). | Config/Security | `config/runtime_credentials.py` | Crítica | Alta | system | Infra/Security | @security @infra | Alta | 12 | Médio | **736** | 40 → 85 | Não | 🔲 Pendente |
| **IMP-003** | Modularizar `app.js` em bundles por domínio (dashboard/settings/jobs), adicionar lint/tests e reaproveitar fetch helpers (`Linhas ≈250`, `PesoCamada=2`, `debt_ratio=0.15`). | Frontend Web | `src/interfaces/web/static` | Média | Média | project | UI | @refactor @frontend | Média | 16 | Médio | **615** | 55 → 78 | Não | 🔲 Pendente |

## Detalhamento (CoCoT + ReAct)

### IMP-001 – Controller fino + presenter reutilizável
- **Comprovação:** `src/interfaces/http/app.py:274-325` mistura consulta, paginação, exportação CSV/JSON e renderização.
- **Causalidade:** Em altos volumes (>20 eventos/job) a rota bloqueia worker uvicorn e dificulta reaproveitamento headless.
- **Contexto:** O container já expõe use cases; basta criar `JobQueryService` e endpoints `/api/jobs/{id}/logs` para a UI usar AJAX.
- **Tendência:** Aplicar padrão Presenter/ViewModel + streaming de logs (SSE/WebSocket) como em sistemas modernos.
- **ReAct (simulação):** Dividir a rota em (1) query service, (2) endpoint REST, (3) template leve. Ganhos: 20‑30% de latência menor e testes isolados. Riscos mitigáveis: garantir cache de `Path.read_text` e limites de página.

### IMP-002 – Segurança de credenciais
- **Comprovação:** `config/runtime_credentials.py:18-64` grava chaves em JSON texto puro.
- **Causalidade:** Viola OWASP ASVS 2.1/PCI e bloqueia auditorias enterprise.
- **Contexto:** Já existe `filelock`; podemos adicionar `cryptography.Fernet` com chave derivada de env (`SETTINGS_SECRET`), versionar por ambiente e registrar data/hora de cada alteração.
- **Tendência:** Integração com AWS KMS/Secrets Manager ou Azure Key Vault quando em produção.
- **ReAct:** Implementar wrapper `SecureCredentialStore` + CLI para rotação. Efeitos: confidencialidade forte, habilita auditorias. Riscos: necessidade de secret bootstrap (documentar fallback dev).

### IMP-003 – Modularização de UI/JS
- **Comprovação:** `src/interfaces/web/static/app.js` >300 linhas concentrando todo comportamento.
- **Causalidade:** Dificulta testes, tree-shaking e adoção de frameworks; cada novo recurso amplia o débito.
- **Contexto:** A UI já utiliza ES modules no navegador moderno; podemos dividir em arquivos (`dashboard.js`, `settings.js`, `jobs.js`), usar Vite/esbuild (sem SPA) e acoplar Jest/Playwright.
- **Tendência:** Microfrontends leves com componentes reativos e bundling incremental.
- **ReAct:** Montar pipeline Vite + npm scripts, mover bindings específicos para módulos e importar no `base.html`. Ganhos: 25% menos JS enviado, cobertura unitária. Riscos moderate: build tooling novo (mitigar com fallback sem bundler).

## Próximos passos operacionais
1. **Kick-off IMP-002 (Segurança)** antes de qualquerDeploy – risco crítico.
2. **Refatoração IMP-001** em paralelo, garantindo contrato JSON para logs/export.
3. **Iniciar IMP-003** após IMP-001, usando os novos endpoints para migrar UI gradualmente.
4. **Gerar relatórios auxiliares** (melhoria log/test validation/telemetry) após cada entrega para manter rastreabilidade Enterprise+.
