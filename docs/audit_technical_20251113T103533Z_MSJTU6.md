# Relatório Técnico – EXEC_ID 20251113T103533Z_MSJTU6

## 1. Visão geral do sistema
- **Stack principal:** FastAPI + aplicação modular em Python (camadas `application/`, `domain/`, `infrastructure/`, `interfaces/`) com UI server-rendered (Jinja2 + JS vanilla) e watcher para processamento de áudio (Whisper/OpenAI + pós-edição ChatGPT).
- **Dependências críticas:** `fastapi`, `faster-whisper`, `pydantic-settings`, `gspread/google-auth`, `filelock`, `jinja2`, `watchdog`. Todas listadas em `requirements.txt`.
- **Fluxo de dados:** jobs entram pela interface/API, são persistidos via repositórios de arquivos/planilhas, processados por use cases e expostos via `/` (dashboard) e `/jobs/{id}` (detalhes).
- **Testes atuais:** `pytest -q` → **45 testes passando** (apenas `DeprecationWarning` do httpx). Não há medição de cobertura e não existem testes dedicados para o front.

## 2. Inventário arquitetural
| Camada | Principais módulos | Observações |
| --- | --- | --- |
| **Domain** | `domain/entities/job.py`, `value_objects.py` | Modelos enxutos, porém sem validações profundas ou invariantes explícitas. |
| **Application** | `application/controllers/*`, `services/oauth_service.py` | Use cases desacoplados via container, mas controllers concentram lógica de transformação. |
| **Infrastructure** | `infrastructure/container`, `config/*`, `runtime_credentials.py` | Container e stores em filesystem. API keys são persistidas em JSON simples. |
| **Interfaces** | `interfaces/http/app.py`, `interfaces/web/static/app.js` | FastAPI para rotas HTTP + JS vanilla de ~330 linhas para UX dinâmica. |

## 3. Métricas e gaps
- **Complexidade ciclomática:** `src/interfaces/http/app.py:274-325` (`job_detail`) possui ~50+ linhas tratando filtro/paginação/exportação, leitura de arquivos e rendering – fora do limite recomendado para controllers simples (SRP).
- **Acoplamento:** Controllers instanciam diretamente o container (`get_container()`), criando dependência forte da camada de infraestrutura.
- **Segurança:** `config/runtime_credentials.py:18-64` grava chaves Whisper/ChatGPT em `config/runtime_credentials.json` sem criptografia, rotação ou segregação por ambiente.
- **Frontend:** `src/interfaces/web/static/app.js` concentra todos os comportamentos de UI (toasts, polling, AJAX, modais, skeletons) em um único arquivo de +300 linhas, dificultando testes e reuso.
- **Observabilidade:** Logs e métricas estão confinados a watchers; não há dashboards de telemetria ou métricas persistidas conforme solicitado no prompt (ex.: `/docs/improvement_telemetry.json` inexistente).

## 4. Achados principais (CoCoT)

### 4.1 Controller de detalhes com IO e formatação misturados
- **Comprovação:** `src/interfaces/http/app.py:274-325` lê arquivos (`Path.read_text`), pagina logs, exporta CSV/JSON e renderiza templates no mesmo método.
- **Causalidade:** Mistura de responsabilidades aumenta o tempo de resposta e a chance de regressões (qualquer mudança na UI exige tocar na lógica de negócio e vice-versa).
- **Contexto:** A aplicação segue princípios de Clean/Hexagonal, porém esse endpoint viola SRP e torna difícil reaproveitar a mesma lógica para API headless.
- **Tendência:** Extrair um `JobDetailPresenter`/`QueryService` especializado e mover o IO para serviços assíncronos (ou background tasks) mantém o controller fino e alinhado a arquiteturas modernas.

### 4.2 Credenciais persistidas em texto puro
- **Comprovação:** `config/runtime_credentials.py:18-64` usa JSON local + `filelock` para guardar chaves Whisper/ChatGPT sem criptografia.
- **Causalidade:** Vazamentos de `config/runtime_credentials.json` (commit acidental, backup inseguro) expõem segredos de produção e violam PCI/OWASP ASVS 2.1.
- **Contexto:** O projeto já depende de `filelock` e rodará em ambientes multiusuário; proteger segredos é obrigatório antes de qualquer deploy enterprise.
- **Tendência:** Utilizar `keyring`, KMS (AWS/GCP) ou pelo menos criptografia simétrica (libsodium/Fernet) com rotação automática é prática padrão em 2025.

### 4.3 Frontend monolítico sem contrato forte
- **Comprovação:** `src/interfaces/web/static/app.js` concentra polling, toasts, modais, AJAX de settings e fluxo de processamento; não há módulos ou testes dedicados.
- **Causalidade:** Código com 300+ linhas torna difícil aplicar linting/tests, aumenta risco de regressões e dificulta adoção futura de componentes reativos (React/Vue).
- **Contexto:** A UI precisa crescer (feature flags, dashboards, paginação). Sem modularização, qualquer novo recurso repete padrões e agrava débito.
- **Tendência:** Dividir em módulos ES (`/static/js/dashboard.js`, `/static/js/settings.js`) ou migrar gradualmente para bundler Vite/Rollup com testes Jest/Playwright.

### 4.4 Observabilidade e relatórios pendentes
- **Comprovação:** Pastas `/docs` não possuem `audit_technical`, `improvement_plan`, `improvement_log`, `cross_module_impact`, etc., exigidos pelo prompt Enterprise+.
- **Causalidade:** Sem relatórios e telemetria, não há rastreabilidade de mudanças nem insumos para SLAs.
- **Contexto:** O processo Enterprise+ depende desses artefatos para liberar releases e alimentar sistemas externos (Slack/Teams).
- **Tendência:** Automatizar geração de relatórios via scripts (`scripts/generate_audit.py`) e armazenar telemetria em JSON versionado (OpenTelemetry exporters).

## 5. Recomendações imediatas
1. **Refatorar controllers pesados** movendo leitura/paginação/exportação para serviços especializados, expondo endpoints REST/JSON reutilizáveis.
2. **Endurecer armazenamento de segredos** (criptografia + segregação por ambiente) e adicionar trilhas de auditoria a cada alteração em `/settings/api`.
3. **Modularizar o front** criando entradas separadas (dashboard/actions/settings) com build pipeline simples (esbuild/Vite) + testes estáticos.
4. **Automatizar relatórios e telemetria** para atender o checklist Enterprise (audit, improvement plan, telemetry JSON, rollback log).

Essas ações pavimentam a próxima etapa: implementação do plano de melhorias e geração contínua dos artefatos exigidos.
