# Cobertura de Testes (relatório parcial)

- **Base analisada**: `artifacts/unit/coverage.xml` (linha-rate geral: `0.8631`, branch-rate `0`).
- **Cobertura de branches**: não foi gerada (`branch-rate=0`). A configuração atual do coverage não ativa `branch = True`.

## Principais gaps identificados (linhas sem hits)

| Arquivo | Lições não cobertas (linhas) | Tipo provável de fluxo |
| --- | --- | --- |
| `application/services/delivery_template_service.py` | 50, 58, 61, 116, 117, 125, 129, 132, 143 | falhas de template ausente/malformado, front matter inválido e renderização condicional |
| `application/services/accuracy_service.py` | 127, 143, 150, 152, 176-183 | cálculos de penalidade e WER com flags de confiança baixa |
| `application/services/whisper_service.py` | 102-120 | chunking alternativo, fallback quando `Pydub` ausente ou chunk trigger ativado |
| `application/services/webhook_service.py` | 49, 50, 57, 58, 74, 77, 78, 89 | rotinas de assinatura + resolução de segredos, também usadas por webhook_routes |
| `application/services/oauth_service.py` | 19, 34 | roteiros de erro (sem `authorize url`, troca de código com falha) |
| `application/services/session_service.py` | 51-53, 69, 83-84 | criação/validação de sessões expiradas e geração de CSRF |
| `application/services/job_log_service.py` | 38-84 | filtragem/paginação de log (métricas de nível e busca) |
| `application/services/sheet_service.py` | 45-47 | escrita em CSV e fallback em gateway do Google Sheets |
| `application/services/artifact_builder.py` | 97-110 | geração de TXT/JSON com template e validation warnings |
| `application/services/chatgpt_service.py` | 84 | fallback ao parse JSON invalido do ChatGPT |
| `domain/usecases/*.py` | várias (ex.: `run_asr.py`, `generate_artifacts.py`, `retry_or_reject.py`) | fluxos de exceção/retry |
| `infrastructure/api/*` | (Whisper, OpenAI, GoTranscript) | caminhos dependentes de `requests`/`files` |
| `interfaces/http/app.py` | muitas linhas | endpoints/dashboards com autenticação/session/context |

## Próximas ações sugeridas (parte do plano de testes)

1. **Ativar cobertura de branches** alterando `.coveragerc`/`pytest.ini` para `branch = True` e garantindo que `pytest` registre dados de `branch` (`--cov-branch`).
2. **Adicionar testes unitários** para:
   - Garantir que `DeliveryTemplateService` falhe com template ausente e valide front matter.
   - Testar `WebhookService` e `OAuthService` com segredos ausentes e falhas de rede.
   - Cobrir `JobLogService`, `SessionService` e `SheetService` nos caminhos de erro (CSV/planilha não disponíveis, sessão expirada, etc.).
3. **Criar integrações** (mockando APIS externas) para:
   - `WhisperService` + `AudioChunker` com chunking e fallback sem `pydub`.
   - `JobController` + `ProcessJobPipeline` para garantir integração job → log → status.
4. **Verificar e2e** com stub atualizado (incluindo o suporte a `list_jobs(limit, page)` corrigido) para garantir dashboard/job detail/excl. os elementos esperados.
5. **Plano de load**: registrar script em `tests/load/` que envia N jobs e mede latência e erros (podemos usar `k6` ou `pytest-benchmark` no futuro breve).

## Como rodar cobertura com branches

- Atualize o ambiente com `pip install -r requirements.txt pytest-cov` (já presente no CI).  
- Use `pytest --cov=src --cov-branch --cov-report=xml --cov-report=html` para gerar relatórios de linhas e branches.  
- `coverage.xml` (Cobertura) e `htmlcov/` aparecem no root.  
- Meta sugerida: `linhas ≥ 95%`, `branches ≥ 70%`. Se os branches ainda estiverem baixos, adicione testes que cubram paths de exceção e fallback.

Registrar essa visão em um capítulo de documentação ajuda a manter alinhado o pipeline CI/CD e guiar novos testes.
