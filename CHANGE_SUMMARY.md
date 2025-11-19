# CHANGE_SUMMARY

- EXEC_ID: 20251113T103533Z_MSJTU6
- Registro obrigatório de cada modificação relevante (arquivo, operação, justificativa, versão e timestamp UTC).

| Timestamp (UTC) | Arquivo | Operação | Justificativa Técnica | Versão |
| --- | --- | --- | --- | --- |
| 2025-11-13T10:36:05Z | docs/EXEC_ESTIMATE_20251113T103533Z_MSJTU6.md | Criação | Registrar estimativa obrigatória antes da implementação | v1 |
| 2025-11-13T10:36:05Z | REVIEW_LOG.md | Criação | Abrir log de revisões conforme governança exigida | v1 |
| 2025-11-13T10:36:05Z | CHANGE_SUMMARY.md | Criação | Inicializar tabela de rastreabilidade de alterações | v1 |
| 2025-11-13T10:37:58Z | .env.example | Criação | Definir variáveis obrigatórias para configuração do sistema | v1 |
| 2025-11-13T10:37:58Z | config/__init__.py | Criação | Expor helper `get_settings` e padronizar cache de configurações | v1 |
| 2025-11-13T10:37:58Z | config/settings.py | Criação | Implementar carregamento Pydantic das variáveis com validação | v1 |
| 2025-11-13T10:37:58Z | config/profile_loader.py | Criação | Adicionar parser de perfis `.prompt.txt` com front matter YAML | v1 |
| 2025-11-13T10:37:58Z | profiles/geral.prompt.txt | Criação | Disponibilizar perfil editorial padrão requerido pelos fluxos | v1 |
| 2025-11-13T10:37:58Z | output/log.csv | Criação | Iniciar registro tabular de eventos e jobs conforme requisito | v1 |
| 2025-11-13T10:37:58Z | src/__init__.py | Criação | Marcar pacote raiz para permitir importações organizadas | v1 |
| 2025-11-13T10:37:58Z | src/domain/__init__.py | Criação | Marcar pacote de domínio | v1 |
| 2025-11-13T10:37:58Z | src/domain/entities/__init__.py | Criação | Marcar subpacote de entidades | v1 |
| 2025-11-13T10:37:58Z | src/domain/usecases/__init__.py | Criação | Marcar subpacote de casos de uso | v1 |
| 2025-11-13T10:37:58Z | src/application/__init__.py | Criação | Marcar camada de aplicação | v1 |
| 2025-11-13T10:37:58Z | src/application/services/__init__.py | Criação | Marcar subpacote de serviços de aplicação | v1 |
| 2025-11-13T10:37:58Z | src/application/controllers/__init__.py | Criação | Marcar subpacote de controllers | v1 |
| 2025-11-13T10:37:58Z | src/infrastructure/__init__.py | Criação | Marcar camada de infraestrutura | v1 |
| 2025-11-13T10:37:58Z | src/infrastructure/database/__init__.py | Criação | Marcar subpacote de persistência | v1 |
| 2025-11-13T10:37:58Z | src/infrastructure/api/__init__.py | Criação | Marcar subpacote de integrações externas | v1 |
| 2025-11-13T10:37:58Z | src/interfaces/__init__.py | Criação | Marcar camada de interfaces | v1 |
| 2025-11-13T10:37:58Z | src/interfaces/http/__init__.py | Criação | Marcar subpacote HTTP/FastAPI | v1 |
| 2025-11-13T10:37:58Z | src/interfaces/cli/__init__.py | Criação | Marcar subpacote CLI | v1 |
| 2025-11-13T10:37:58Z | src/interfaces/web/__init__.py | Criação | Marcar subpacote Web/UI | v1 |
| 2025-11-13T10:37:58Z | src/interfaces/web/pages/__init__.py | Criação | Marcar subpacote de páginas web | v1 |
| 2025-11-13T10:37:58Z | src/interfaces/web/components/__init__.py | Criação | Marcar subpacote de componentes web | v1 |
| 2025-11-13T10:38:55Z | REVIEW_LOG.md | Atualização | Reescrever em ASCII e registrar revisões dos blocos 1 e 2 | v2 |
| 2025-11-13T10:40:45Z | src/domain/entities/value_objects.py | Criação | Definir enums essenciais de status, engine e tipos de artefato | v1 |
| 2025-11-13T10:40:45Z | src/domain/entities/transcription.py | Criação | Estruturar modelos para segmentos e resultados de ASR/pós-edição | v1 |
| 2025-11-13T10:40:45Z | src/domain/entities/job.py | Criação | Implementar entidade Job com regras básicas de status e artefatos | v1 |
| 2025-11-13T10:40:45Z | src/domain/entities/profile.py | Criação | Representar perfis editoriais com helpers de legenda/anonymização | v1 |
| 2025-11-13T10:40:45Z | src/domain/entities/artifact.py | Criação | Modelar artefatos gerados por job | v1 |
| 2025-11-13T10:40:45Z | src/domain/entities/log_entry.py | Criação | Estruturar logs operacionais de domínio | v1 |
| 2025-11-13T10:40:45Z | src/domain/entities/user_review.py | Criação | Representar revisões humanas exigidas pelo fluxo | v1 |
| 2025-11-13T10:40:45Z | src/domain/ports/__init__.py | Criação | Inicializar pacote de portas de domínio | v1 |
| 2025-11-13T10:40:45Z | src/domain/ports/repositories.py | Criação | Definir contratos de repositórios (jobs, artefatos, logs, reviews) | v1 |
| 2025-11-13T10:40:45Z | src/domain/ports/services.py | Criação | Definir contratos de serviços (ASR, pós-edição, artefatos, pacotes) | v1 |
| 2025-11-13T10:43:32Z | src/domain/entities/job.py | Atualização | Incluir metadados adicionais no Job e simplificar vínculo de artefatos | v2 |
| 2025-11-13T10:43:32Z | src/domain/usecases/create_job.py | Criação | Caso de uso para registrar jobs detectados no inbox | v1 |
| 2025-11-13T10:43:32Z | src/domain/usecases/run_asr.py | Criação | Caso de uso que orquestra execução do ASR | v1 |
| 2025-11-13T10:43:32Z | src/domain/usecases/post_edit.py | Criação | Caso de uso para pós-edição com GPT | v1 |
| 2025-11-13T10:43:32Z | src/domain/usecases/generate_artifacts.py | Criação | Caso de uso para gerar artefatos padrões (TXT/SRT/VTT/JSON) | v1 |
| 2025-11-13T10:43:32Z | src/domain/usecases/register_delivery.py | Criação | Caso de uso para pacotes ZIP e registro de entrega | v1 |
| 2025-11-13T10:43:32Z | src/domain/usecases/handle_review.py | Criação | Caso de uso de revisão humana e atualização de status | v1 |
| 2025-11-13T10:43:32Z | src/domain/usecases/retry_or_reject.py | Criação | Caso de uso para refileirar ou rejeitar jobs com falha | v1 |
| 2025-11-13T10:43:32Z | src/domain/usecases/pipeline.py | Criação | Orquestração fim a fim do pipeline do job | v1 |
| 2025-11-13T10:45:56Z | src/application/services/ports.py | Criação | Definir clientes abstratos para ASR, ChatGPT e Sheets | v1 |
| 2025-11-13T10:45:56Z | src/application/services/retry.py | Criação | Implementar executor de retentativas com backoff | v1 |
| 2025-11-13T10:45:56Z | src/application/services/whisper_service.py | Criação | Serviço ASR concreto com seleção entre engines | v1 |
| 2025-11-13T10:45:56Z | src/application/services/pii.py | Criação | Helper de anonimização de PII para perfis sensíveis | v1 |
| 2025-11-13T10:45:56Z | src/application/services/chatgpt_service.py | Criação | Serviço de pós-edição estruturada usando ChatGPT | v1 |
| 2025-11-13T10:45:56Z | src/application/services/validator_service.py | Criação | Validador de segments conforme regras de legenda | v1 |
| 2025-11-13T10:45:56Z | src/application/services/subtitle_formatter.py | Criação | Formatter para gerar SRT/VTT obedecendo perfil | v1 |
| 2025-11-13T10:45:56Z | src/application/services/sheet_service.py | Criação | Serviço CSV/Sheets para registro operacional | v1 |
| 2025-11-13T10:50:59Z | .env.example | Atualização | Acrescentar variáveis de Sheets/S3 conforme integrações opcionais | v2 |
| 2025-11-13T10:50:59Z | config/settings.py | Atualização | Suportar novos campos de Sheets e S3 | v2 |
| 2025-11-13T10:50:59Z | src/infrastructure/database/serializers.py | Criação | Serializar entidades para armazenamento em arquivos JSON | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/database/job_repository.py | Criação | Repositório de jobs baseado em arquivo JSON | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/database/artifact_repository.py | Criação | Repositório de artefatos | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/database/log_repository.py | Criação | Repositório de logs operacionais | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/database/review_repository.py | Criação | Repositório de revisões humanas | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/database/profile_provider.py | Criação | Provider que carrega perfis do filesystem | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/api/openai_client.py | Criação | Clientes HTTP para Whisper e Chat GPT-4.x | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/api/faster_whisper_client.py | Criação | Adapter para faster-whisper local | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/api/sheets_client.py | Criação | Gateway para Google Sheets | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/api/storage_client.py | Criação | Clientes de armazenamento local/S3 | v1 |
| 2025-11-13T10:50:59Z | src/infrastructure/container.py | Criação | Container de dependências com wiring de serviços e casos de uso | v1 |
| 2025-11-13T10:50:59Z | src/interfaces/cli/watch_inbox.py | Criação | Watcher watchdog para inbox com disparo de pipeline | v1 |
| 2025-11-13T10:50:59Z | scripts/watch_inbox.py | Criação | Script de entrada para executar o watcher | v1 |
| 2025-11-13T10:53:31Z | src/application/controllers/job_controller.py | Criação | Controller para listar/processar jobs expostos pelas interfaces | v1 |
| 2025-11-13T10:53:31Z | src/application/controllers/review_controller.py | Criação | Controller para revisão humana e logging | v1 |
| 2025-11-13T10:53:31Z | src/infrastructure/container.py | Atualização | Incluir wiring do caso de uso HandleReviewDecision | v2 |
| 2025-11-13T10:53:31Z | src/interfaces/http/app.py | Criação | FastAPI app com rotas HTML/API para revisão e processamento | v1 |
| 2025-11-13T10:53:31Z | src/interfaces/web/templates/base.html | Criação | Template base da UI de revisão | v1 |
| 2025-11-13T10:53:31Z | src/interfaces/web/templates/jobs.html | Criação | Listagem de jobs recentes | v1 |
| 2025-11-13T10:53:31Z | src/interfaces/web/templates/job_detail.html | Criação | Detalhe do job com preview e formulário de revisão | v1 |
| 2025-11-13T10:53:31Z | src/interfaces/web/static/styles.css | Criação | Estilos básicos da UI | v1 |
| 2025-11-13T10:53:31Z | src/interfaces/cli/run_job.py | Criação | CLI para criar/processar jobs manualmente | v1 |
| 2025-11-13T10:53:31Z | scripts/run_job.py | Criação | Script de entrada para a CLI de processamento | v1 |
| 2025-11-13T10:56:29Z | src/domain/ports/services.py | Atualização | Ajustar assinatura do ArtifactBuilder para incluir profile | v2 |
| 2025-11-13T10:56:29Z | src/domain/usecases/generate_artifacts.py | Atualização | Recuperar perfil via provider antes de gerar artefatos | v2 |
| 2025-11-13T10:56:29Z | src/application/services/artifact_builder.py | Criação | Builder responsável por TXT/SRT/VTT/JSON com headers | v1 |
| 2025-11-13T10:56:29Z | src/application/services/package_service.py | Criação | Serviço de pacotes ZIP e upload opcional | v1 |
| 2025-11-13T10:56:29Z | src/infrastructure/container.py | Atualização | Ligar builder, package service, storage e register_delivery | v3 |
| 2025-11-13T10:56:29Z | src/application/controllers/review_controller.py | Atualização | Invocar RegisterDelivery quando aprovado | v2 |
| 2025-11-13T10:56:29Z | src/interfaces/http/app.py | Atualização | Disponibilizar register_delivery no controller de revisão | v2 |
| 2025-11-13T10:57:26Z | docs/ERROR_LOG_20251113T103533Z_MSJTU6.md | Criação | Registrar ocorrências críticas (nenhuma nesta execução) | v1 |
| 2025-11-13T10:57:26Z | FEEDBACK_LEARN.md | Criação | Documentar lições aprendidas e próximos focos | v1 |
| 2025-11-13T10:58:30Z | requirements.txt | Criação | Listar dependências obrigatórias do projeto | v1 |
| 2025-11-13T11:11:49Z | tests/conftest.py | Criação | Ajustar PYTHONPATH para permitir importações dos módulos reais | v1 |
| 2025-11-13T11:11:49Z | tests/unit/domain/test_create_job.py | Criação | Validar criação de jobs e logs conforme use case real | v1 |
| 2025-11-13T11:11:49Z | tests/unit/domain/test_run_asr_pipeline.py | Criação | Garantir status/transições do pipeline ASR e cenários de falha | v1 |
| 2025-11-13T11:11:49Z | tests/unit/application/test_whisper_service.py | Criação | Cobrir seleção de engine e mapeamento de segmentos do WhisperService | v1 |
| 2025-11-13T11:11:49Z | tests/unit/application/test_chatgpt_service.py | Criação | Validar pós-edição com mascaramento de PII e prompts reais | v1 |
| 2025-11-13T11:11:49Z | tests/unit/application/test_subtitle_and_validator.py | Criação | Testar formatter SRT/VTT e validator de CPS baseado em regras do perfil | v1 |
| 2025-11-13T11:11:49Z | tests/unit/application/test_artifact_builder_and_package.py | Criação | Exercitar geração de TXT/SRT/VTT/JSON e empacotamento ZIP | v1 |
| 2025-11-13T11:11:49Z | tests/integration/test_pipeline_and_review.py | Criação | Simular pipeline completo + revisão com entrega/planilha | v1 |
| 2025-11-13T11:11:49Z | requirements.txt | Atualização | Incluir pytest para viabilizar a suíte criada | v2 |
| 2025-11-13T11:16:32Z | src/domain/ports/services.py | Atualização | Adicionar contrato para logger de jobs rejeitados | v3 |
| 2025-11-13T11:16:32Z | src/application/services/rejected_logger.py | Criação | Implementar logger filesystem para pasta rejected/ | v1 |
| 2025-11-13T11:16:32Z | src/infrastructure/container.py | Atualização | Injetar FilesystemRejectedLogger e propagar ao RetryOrRejectJob | v4 |
| 2025-11-13T11:16:32Z | src/domain/usecases/retry_or_reject.py | Atualização | Registrar falhas em rejected/ e aceitar metadados do estágio | v2 |
| 2025-11-13T11:16:32Z | src/domain/usecases/pipeline.py | Atualização | Propagar contexto de estágio/payload ao handler de falhas | v2 |
| 2025-11-13T11:16:32Z | tests/unit/domain/test_retry_or_reject.py | Criação | Cobrir escrita real em rejected/ pelo RetryOrRejectJob | v1 |
| 2025-11-13T11:16:32Z | tests/integration/test_pipeline_and_review.py | Atualização | Validar geração de logs rejected/ em falhas de pipeline | v2 |
| 2025-11-13T11:24:26Z | src/domain/ports/services.py | Atualização | Incluir contrato JobStatusPublisher para propagar status | v4 |
| 2025-11-13T11:24:26Z | src/application/services/status_publisher.py | Criação | Adaptador que publica status no CsvSheetService | v1 |
| 2025-11-13T11:24:26Z | src/domain/usecases/create_job.py | Atualização | Notificar sheet a cada job criado via status publisher | v2 |
| 2025-11-13T11:24:26Z | src/domain/usecases/run_asr.py | Atualização | Registrar status PROCESSING/ASR_COMPLETED/FAILED no publisher | v2 |
| 2025-11-13T11:24:26Z | src/domain/usecases/post_edit.py | Atualização | Publicar status POST_EDITING/FAILED automaticamente | v2 |
| 2025-11-13T11:24:26Z | src/domain/usecases/generate_artifacts.py | Atualização | Publicar status AWAITING_REVIEW após geração dos artefatos | v2 |
| 2025-11-13T11:24:26Z | src/domain/usecases/handle_review.py | Atualização | Delegar registro de status aprovado/ajustes ao publisher | v2 |
| 2025-11-13T11:24:26Z | src/domain/usecases/retry_or_reject.py | Atualização | Incluir publisher para jobs refileirados ou rejeitados | v3 |
| 2025-11-13T11:24:26Z | src/infrastructure/container.py | Atualização | Instanciar SheetStatusPublisher e injetar em todos os use cases | v5 |
| 2025-11-13T11:24:26Z | src/interfaces/cli/watch_inbox.py | Atualização | Remover escrita duplicada no CSV (agora feita pelo publisher) | v2 |
| 2025-11-13T11:24:26Z | src/application/controllers/review_controller.py | Atualização | Evitar registro duplicado; rely on status publisher | v3 |
| 2025-11-13T11:24:26Z | tests/conftest.py | Atualização | Garantir sys.path (raiz/src) e stubs para libs ausentes | v2 |
| 2025-11-13T11:24:26Z | tests/unit/domain/test_create_job.py | Atualização | Cobrir notificação do status publisher ao criar job | v2 |
| 2025-11-13T11:24:26Z | tests/unit/domain/test_run_asr_pipeline.py | Atualização | Verificar publicação de status durante o ASR | v2 |
| 2025-11-13T11:24:26Z | tests/integration/test_http_api.py | Criação | Exercitar rotas FastAPI com TestClient e download de artefatos | v1 |
| 2025-11-13T11:24:26Z | tests/integration/test_cli_run_job.py | Criação | Validar CLI run_job com container/JobController stubs | v1 |
| 2025-11-13T11:31:52Z | tests/integration/test_http_api.py | Atualização | Cobrir submissão de review (Form) e ajustes de config | v2 |
| 2025-11-13T11:31:52Z | tests/integration/test_watcher.py | Criação | Simular watcher processando áudio e disparando pipeline | v1 |
| 2025-11-13T11:31:52Z | tests/conftest.py | Atualização | Tornar import de dependências condicional e compatível com libs reais | v3 |
| 2025-11-13T11:41:58Z | src/application/services/status_publisher.py | Atualização | Tornar publicação resiliente a falhas de Sheets com log de warning | v2 |
| 2025-11-13T11:41:58Z | tests/unit/application/test_status_publisher.py | Criação | Validar comportamento do publisher em sucesso/falha | v1 |
| 2025-11-13T11:41:58Z | tests/integration/test_http_api.py | Atualização | Adicionar caso de revisão com ajuste negativo | v3 |
| 2025-11-13T11:41:58Z | tests/integration/test_openai_adapters.py | Criação | Testes de contrato para clientes HTTP (Whisper/Chat) | v1 |
| 2025-11-13T11:41:58Z | tests/integration/test_faster_whisper_adapter.py | Criação | Validar adapter local usando stub de WhisperModel | v1 |
| 2025-11-13T11:41:58Z | tests/integration/test_pipeline_and_review.py | Atualização | Cobrir falha em geração de artefatos com stage=artifacts | v3 |
| 2025-11-13T11:41:58Z | tests/integration/test_watcher.py | Atualização | Acrescentar smoke end-to-end com pipeline real e geração de artefatos | v2 |
| 2025-11-13T11:52:41Z | src/interfaces/http/app.py | Atualização | Ajustar TemplateResponse para formato recomendado e remover warnings | v3 |
| 2025-11-13T11:52:41Z | tests/support/stubs.py | Criação | Centralizar repositórios e serviços stub compartilhados | v1 |
| 2025-11-13T11:52:41Z | tests/integration/test_watcher.py | Atualização | Reutilizar stubs compartilhados e refinar smoke test | v3 |
| 2025-11-13T11:52:41Z | tests/performance/test_pipeline_performance.py | Criação | Medir tempo médio do pipeline real e impor limite | v1 |
| 2025-11-13T11:52:41Z | tests/performance/test_http_performance.py | Criação | Avaliar latência média das rotas FastAPI | v1 |
| 2025-11-13T11:53:34Z | docs/TEST_PROMPTS.md | Criação | Documentar prompts e roteiros para repetir testes/performance | v1 |
| 2025-11-13T12:05:38Z | requirements.txt | Atualização | Adicionar dependência filelock para garantir locks em CSV/JSON | v3 |
| 2025-11-13T12:05:38Z | src/infrastructure/database/file_storage.py | Criação | Utilitário centralizado de leitura/escrita com file lock | v1 |
| 2025-11-13T12:05:38Z | src/infrastructure/database/job_repository.py | Atualização | Usar locks em operações JSON para evitar corrupção concorrente | v2 |
| 2025-11-13T12:05:38Z | src/infrastructure/database/artifact_repository.py | Atualização | Aplicar file locks na persistência de artefatos | v2 |
| 2025-11-13T12:05:38Z | src/infrastructure/database/log_repository.py | Atualização | Garantir locking na escrita/leituras de logs | v2 |
| 2025-11-13T12:05:38Z | src/infrastructure/database/review_repository.py | Atualização | Proteger arquivo de reviews com locks atômicos | v2 |
| 2025-11-13T12:05:38Z | src/application/services/sheet_service.py | Atualização | Serializar append no CSV via filelock | v2 |
| 2025-11-13T12:11:46Z | src/infrastructure/container/service_container.py | Criação | Modularizar wiring do container em componentes menores | v1 |
| 2025-11-13T12:11:46Z | src/infrastructure/container/__init__.py | Criação | Reexportar container modular | v1 |
| 2025-11-13T12:11:46Z | src/infrastructure/container/components_storage.py | Criação | Construtores de repositórios/profiles | v1 |
| 2025-11-13T12:11:46Z | src/infrastructure/container/components_asr.py | Criação | Wiring de ASR/post-edit/review com serviços compartilhados | v1 |
| 2025-11-13T12:11:46Z | src/infrastructure/container/components_artifacts.py | Criação | Factory para builder e use case de artefatos | v1 |
| 2025-11-13T12:11:46Z | src/infrastructure/container/components_delivery.py | Criação | Sheet/status publisher e serviços de entrega | v1 |
| 2025-11-13T12:11:46Z | tests/support/stubs.py | Criação | Centralizar stubs e threads para testes | v1 |
| 2025-11-13T12:11:46Z | tests/integration/test_watcher.py | Atualização | Reaproveitar stubs compartilhados e validar texto pós pipeline | v4 |
| 2025-11-13T12:11:46Z | tests/performance/test_pipeline_performance.py | Atualização | Ajustar threshold após locks e uso de novo pipeline modular | v2 |
| 2025-11-13T12:12:11Z | config/settings.py | Atualização | Adicionar limites configuráveis de request e tamanho de áudio | v3 |
| 2025-11-13T12:12:11Z | src/application/logging_config.py | Criação | Configurar logging estruturado em JSON | v1 |
| 2025-11-13T12:12:11Z | src/interfaces/cli/watch_inbox.py | Atualização | Substituir prints por logger e validar limite de arquivo | v3 |
| 2025-11-13T12:12:11Z | src/interfaces/http/app.py | Atualização | Incluir middleware de limite de payload e logging | v4 |
| 2025-11-13T12:12:11Z | tests/integration/test_http_api.py | Atualização | Cobrir middleware de limite e ajustar overrides de settings | v4 |
| 2025-11-13T12:12:11Z | tests/integration/test_watcher.py | Atualização | Adicionar cenário de arquivo excedendo limite | v5 |
| 2025-11-13T12:40:39Z | src/interfaces/http/app.py | Atualização | Middleware de limite, logging e monitoramento de downloads | v5 |
| 2025-11-13T12:47:10Z | config/settings.py | Atualização | Acrescentar parâmetros de chunking e ampliar limites padrão | v4 |
| 2025-11-13T12:47:10Z | src/application/services/audio_chunker.py | Criação | Utilitário para dividir áudios longos antes do ASR | v1 |
| 2025-11-13T12:47:10Z | src/application/services/whisper_service.py | Atualização | Suportar chunking com offsets e metadados | v2 |
| 2025-11-13T12:47:10Z | src/infrastructure/container/components_asr.py | Atualização | Injetar AudioChunker e configurar thresholds | v2 |
| 2025-11-13T12:47:10Z | tests/unit/application/test_whisper_service.py | Atualização | Cobrir agregação de chunks e novos stubs | v3 |
| 2025-11-13T12:47:10Z | tests/integration/test_http_api.py | Atualização | Adicionar teste para 413 e ajustar overrides | v5 |
| 2025-11-13T12:47:10Z | tests/integration/test_watcher.py | Atualização | Garantir que SmokeContainer respeita limite configurável | v6 |
| 2025-11-13T12:47:10Z | tests/support/domain.py | Criação | Centralizar stubs/fixtures de domínio reutilizáveis | v1 |
| 2025-11-13T12:47:10Z | tests/unit/domain/test_run_asr_pipeline.py | Atualização | Reutilizar stubs compartilhados e reduzir duplicação | v3 |
| 2025-11-13T12:47:10Z | tests/unit/domain/test_retry_or_reject.py | Atualização | Reutilizar repos/loggers compartilhados | v2 |
| 2025-11-13T12:55:55Z | tests/support/domain.py | Cria��o | Stubs/fixtures compartilhados para testes de dom�nio | v1 |
| 2025-11-13T12:55:55Z | tests/unit/domain/test_run_asr_pipeline.py | Atualiza��o | Migrar para fixtures compartilhadas | v3 |
| 2025-11-13T12:55:55Z | tests/unit/domain/test_retry_or_reject.py | Atualiza��o | Reutilizar stubs compartilhados | v3 |
| 2025-11-13T12:55:55Z | config/settings.py | Atualiza��o | Definir limites padr�o maiores e lista de extens�es | v5 |
| 2025-11-13T12:55:55Z | src/interfaces/http/app.py | Atualiza��o | Whitelist de extens�es e testes associados | v6 |
| 2025-11-13T12:55:55Z | tests/integration/test_http_api.py | Atualiza��o | Ajustar overrides + validar extens�es | v6 |
| 2025-11-13T12:55:55Z | tests/performance/test_pipeline_performance.py | Atualiza��o | Threshold alinhado ao chunking | v3 |
| 2025-11-13T13:18:02Z | src/interfaces/http/dependencies.py | Criacao | Criar provedor compartilhado de Settings/WebhookService para DI e testes | v1 |
| 2025-11-13T13:18:02Z | src/interfaces/http/auth_routes.py | Atualizacao | Remover dependencia do container e usar DI direta de Settings no OAuth | v2 |
| 2025-11-13T13:18:02Z | src/application/services/webhook_service.py | Criacao | Centralizar validacao HMAC, trace IDs e erros estruturados de webhooks | v1 |
| 2025-11-13T13:18:02Z | src/interfaces/http/webhook_routes.py | Atualizacao | Integrar WebhookService, cabecalho X-Integration-Id e resposta com trace_id | v2 |
| 2025-11-13T13:18:02Z | tests/integration/test_http_api.py | Atualizacao | Ajustar helper de settings, cobrir OAuth/login e novo fluxo de webhooks | v3 |
| 2025-11-13T13:18:02Z | docs/integration_map_20251113T103533Z_MSJTU6.md | Criacao | Registrar mapa de integracoes com status/riscos conforme governanca | v1 |
| 2025-11-13T13:52:10Z | config/settings.py | Atualizacao | Incluir TTL de sessao para governar expiracao de login OAuth | v2 |
| 2025-11-13T13:52:10Z | src/application/services/session_service.py | Criacao | Persistir sessoes OAuth com TTL e file lock em processing/ | v1 |
| 2025-11-13T13:52:10Z | src/interfaces/http/dependencies.py | Atualizacao | Expor get_session_service e guard de autenticacao para FastAPI | v2 |
| 2025-11-13T13:52:10Z | src/interfaces/http/auth_routes.py | Atualizacao | Finalizar fluxo OAuth com criacao de sessao e cookie seguro | v3 |
| 2025-11-13T13:52:10Z | src/interfaces/http/app.py | Atualizacao | Proteger rotas de UI/API com dependencia require_active_session | v3 |
| 2025-11-13T13:52:10Z | tests/integration/test_http_api.py | Atualizacao | Adaptar overrides, criar teste de guard e validar cookie de sessao | v4 |
| 2025-11-13T13:52:10Z | tests/performance/test_http_performance.py | Atualizacao | Garantir autenticacao simulada em teste de throughput | v2 |
| 2025-11-13T14:18:33Z | config/settings.py | Atualizacao | Adicionar tolerancia/arquivo de segredos de webhook parametrizaveis | v3 |
| 2025-11-13T14:18:33Z | config/webhook_integrations.json | Criacao | Registrar mapeamento padrao de segredos por integracao | v1 |
| 2025-11-13T14:18:33Z | src/application/services/webhook_service.py | Atualizacao | Implementar validacao com timestamp, segredo por integracao e metricas | v2 |
| 2025-11-13T14:18:33Z | src/interfaces/http/dependencies.py | Atualizacao | Cachear WebhookService considerando tolerancia e caminho dos segredos | v3 |
| 2025-11-13T14:18:33Z | src/interfaces/http/webhook_routes.py | Atualizacao | Exigir timestamp, expor metrics/latencia e tratar excecoes genericas | v3 |
| 2025-11-13T14:18:33Z | tests/integration/test_http_api.py | Atualizacao | Ajustar overrides, cabe�alhos e asserts para novo servi�o e guardas | v5 |
| 2025-11-13T14:18:33Z | tests/performance/test_http_performance.py | Atualizacao | Simular sessao em teste de throughput | v3 |
| 2025-11-13T14:28:02Z | docs/integration_plan_20251113T103533Z_MSJTU6.md | Criacao | Plano sequencial para GoTranscript, S3 e observabilidade conforme prompt Enterprise+ | v1 |
| 2025-11-13T14:40:05Z | config/settings.py | Atualizacao | Adicionar flags/parametros da API GoTranscript | v4 |
| 2025-11-13T14:40:05Z | .env.example | Atualizacao | Documentar variaveis GOTRANSCRIPT_* para configuracao | v2 |
| 2025-11-13T14:40:05Z | src/domain/entities/delivery_record.py | Criacao | Representar entregas externas (status, external_id, timestamps) | v1 |
| 2025-11-13T14:40:05Z | src/domain/ports/services.py | Atualizacao | Introduzir DeliveryClient e limpar docstrings ASCII | v3 |
| 2025-11-13T14:40:05Z | src/domain/usecases/register_delivery.py | Atualizacao | Chamar DeliveryClient apos geracao do pacote e registrar log dedicado | v2 |
| 2025-11-13T14:40:05Z | src/infrastructure/api/gotranscript_client.py | Criacao | Cliente HTTP para submissao de pacotes com HMAC/Bearer | v1 |
| 2025-11-13T14:40:05Z | src/infrastructure/container/components_delivery.py | Atualizacao | Injetar GoTranscriptClient quando habilitado na configuracao | v2 |
| 2025-11-13T14:40:05Z | tests/unit/domain/test_register_delivery.py | Criacao | Garantir que RegisterDelivery invoque cliente externo e registre log | v1 |
| 2025-11-13T14:55:41Z | src/infrastructure/api/storage_client.py | Atualizacao | Permitir endpoint/credenciais customizados para S3/MinIO | v2 |
| 2025-11-13T14:55:41Z | src/infrastructure/container/components_delivery.py | Atualizacao | Passar novas configuracoes S3 e wiring padrao | v3 |
| 2025-11-13T14:55:41Z | tests/unit/application/test_sheet_service.py | Criacao | Garantir que CsvSheetService registre CSV + gateway | v1 |
| 2025-11-13T14:55:41Z | docs/integration_map_20251113T103533Z_MSJTU6.md | Atualizacao | Atualizar status das integracoes (GoTranscript, S3, Sheets) | v2 |
| 2025-11-13T15:08:02Z | src/interfaces/http/auth_routes.py | Atualizacao | Adicionar fluxo browser-friendly (redirect) e callback com fallback JSON/HTML | v4 |
| 2025-11-13T15:08:02Z | src/interfaces/http/app.py | Atualizacao | Incluir flash messages na tela de job e acrescentar feedback na revisao | v4 |
| 2025-11-13T15:08:02Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Exibir mensagens de sucesso/ajuste para revisao | v2 |
| 2025-11-13T15:08:02Z | src/interfaces/web/templates/base.html | Atualizacao | Inserir link de login OAuth no menu principal | v2 |
| 2025-11-13T15:08:02Z | docs/frontend_endpoint_usage_20251113T103533Z_MSJTU6.md | Criacao | Inventario de rotas consumidas pela UI | v1 |
| 2025-11-13T15:08:02Z | docs/contract_sync_log_20251113T103533Z_MSJTU6.md | Criacao | Estado de sincronizacao backend/frontend | v1 |
| 2025-11-13T15:08:02Z | tests/integration/test_http_api.py | Atualizacao | Cobrir novo login browser e callback com Accept header | v6 |
| 2025-11-13T15:22:10Z | src/interfaces/http/app.py | Atualizacao | Adicionar flash na home e redirecionar erros de download com job_id | v5 |
| 2025-11-13T15:22:10Z | src/interfaces/http/auth_routes.py | Atualizacao | Callback passa a redirecionar com flash e login/browser usa redirect | v5 |
| 2025-11-13T15:22:10Z | src/interfaces/web/templates/jobs.html | Atualizacao | Exibir mensagens flash no dashboard | v2 |
| 2025-11-13T15:22:10Z | src/interfaces/web/templates/job_detail.html | Recriacao | Normalizar encoding, adicionar flash e job_id nos downloads | v2 |
| 2025-11-13T15:22:10Z | tests/integration/test_http_api.py | Atualizacao | Cobrir callback redirect e download error redirect | v7 |
| 2025-11-13T15:35:18Z | src/interfaces/http/app.py | Atualizacao | Adicionar rota UI de processamento e redirecao amigavel de downloads | v6 |
| 2025-11-13T15:35:18Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Incluir botoes para flash e acionar processamento manual | v3 |
| 2025-11-13T15:35:18Z | tests/integration/test_http_api.py | Atualizacao | Cobrir rota UI de processamento e fallback de download | v8 |
| 2025-11-13T15:47:26Z | src/interfaces/web/static/app.js | Criacao | Adicionar confirmacao JS e estado loading para formularios cr�ticos | v1 |
| 2025-11-13T15:47:26Z | src/interfaces/web/templates/base.html | Atualizacao | Referenciar script de comportamento e manter tema atual | v3 |
| 2025-11-13T15:47:26Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Adicionar confirm modal e bot�o com estado para reprocessar | v4 |
| 2025-11-13T15:47:26Z | src/interfaces/web/static/styles.css | Atualizacao | Estilizar flashes e bot�es em loading | v2 |
| 2025-11-13T15:53:32Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Formularios de revisao agora exigem confirmacao e exibem loading | v5 |
| 2025-11-13T16:03:11Z | src/interfaces/http/app.py | Atualizacao | Adicionar filtros/summary no dashboard e helpers de agregacao | v7 |
| 2025-11-13T16:03:11Z | src/interfaces/web/templates/jobs.html | Atualizacao | Incluir cards de resumo e formulario de filtros responsivo | v3 |
| 2025-11-13T16:03:11Z | src/interfaces/web/static/styles.css | Atualizacao | Estender tema com grid de cards, filtros e layout mobile da tabela | v3 |
| 2025-11-13T16:18:44Z | src/interfaces/http/app.py | Atualizacao | Adicionar filtros/summary e timeline de logs com fallback seguro | v8 |
| 2025-11-13T16:18:44Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Incluir timeline de eventos com badges e log entries | v6 |
| 2025-11-13T16:18:44Z | src/interfaces/web/static/styles.css | Atualizacao | Estilos para timeline/badges e ajustes responsivos | v4 |
| 2025-11-13T16:27:12Z | src/interfaces/web/static/theme.css | Criacao | Definir tokens de cores/tipografia para o tema | v1 |
| 2025-11-13T16:27:12Z | src/interfaces/web/templates/base.html | Atualizacao | Importar theme.css antes de styles.css | v4 |
| 2025-11-13T16:27:12Z | src/interfaces/http/app.py | Atualizacao | Expor resumo/filtros e timeline de logs com fallback | v9 |
| 2025-11-13T16:27:12Z | src/interfaces/web/templates/jobs.html | Atualizacao | Adicionar cards, filtros e responsividade usando tokens | v4 |
| 2025-11-13T16:27:12Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Mostrar timeline de eventos com badges e usar tokens | v7 |
| 2025-11-13T16:27:12Z | src/interfaces/web/static/styles.css | Atualizacao | Refatorar para CSS custom properties e layout mobile | v5 |
| 2025-11-13T16:39:27Z | src/interfaces/web/static/theme.css | Atualizacao | Complementos de tokens p/ future design system (btn/timeline) | v2 |
| 2025-11-13T16:39:27Z | src/interfaces/web/static/styles.css | Atualizacao | Refatoracao para tokens, responsividade e base de componentes | v6 |
| 2025-11-13T16:49:03Z | src/interfaces/web/templates/components/branding.html | Criacao | Branding padrao com logo textual TF | v1 |
| 2025-11-13T16:49:03Z | src/interfaces/web/templates/base.html | Atualizacao | Integrar branding e nav com design tokens | v5 |
| 2025-11-13T16:49:03Z | src/interfaces/http/app.py | Atualizacao | Suporte a logs completos (timeline) | v10 |
| 2025-11-13T16:49:03Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Timeline com link "ver todos" e branding | v8 |
| 2025-11-13T16:49:03Z | src/interfaces/web/static/styles.css | Reescrita | CSS baseado em tokens e responsivo | v7 |
| 2025-11-13T17:00:08Z | src/interfaces/web/static/theme.css | Atualizacao | Suporte a dark mode via prefers-color-scheme | v3 |
| 2025-11-13T17:00:08Z | src/interfaces/web/templates/base.html | Atualizacao | Header usa componente branding reutiliz�vel | v6 |
| 2025-11-13T17:00:08Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Bot�es com classes do tema e link "ver todos" p/ logs | v9 |
| 2025-11-13T17:00:08Z | src/interfaces/web/templates/jobs.html | Atualizacao | Bot�o de filtros usa classes do design system | v5 |
| 2025-11-13T17:00:08Z | src/interfaces/web/static/styles.css | Atualizacao | Reescrever layout com classes .btn, nav e timeline-actions | v8 |
| 2025-11-13T17:00:08Z | docs/ui_theme_reference_20251113T103533Z_MSJTU6.md | Criacao | Documentar tokens e pr�ximos passos do tema | v1 |
| 2025-11-13T17:09:44Z | src/interfaces/web/static/theme.css | Atualizacao | Adicionar modo escuro via media query | v4 |
| 2025-11-13T17:09:44Z | src/interfaces/http/app.py | Atualizacao | Timeline com pagina��o/"ver mais" e �cones | v11 |
| 2025-11-13T17:09:44Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Timeline usa �cones/badges e navega��o | v10 |
| 2025-11-13T17:09:44Z | docs/ui_theme_reference_20251113T103533Z_MSJTU6.md | Atualizacao | Documentar modo escuro e componentes base | v2 |
| 2025-11-13T17:22:33Z | src/interfaces/http/app.py | Atualizacao | Filtro/exportacao de logs via timeline (CSV/JSON) | v12 |
| 2025-11-13T17:22:33Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Filtros de eventos, export links e botoes reutilizando tokens | v11 |
| 2025-11-13T17:34:18Z | src/interfaces/http/app.py | Atualizacao | Painel de eventos cr�ticos e exporta��o de logs (CSV/JSON) | v13 |
| 2025-11-13T17:34:18Z | src/interfaces/web/templates/jobs.html | Atualizacao | Adicionar painel de eventos cr�ticos recentes | v6 |
| 2025-11-13T17:34:18Z | src/interfaces/web/static/styles.css | Atualizacao | Estilos para painel de incidentes e cards log-level | v9 |
| 2025-11-13T17:41:12Z | docs/ui_theme_reference_20251113T103533Z_MSJTU6.md | Atualizacao | Acrescentar painel de incidentes e orientacoes de uso | v3 |
| 2025-11-13T17:50:48Z | src/interfaces/web/templates/components/ui_macros.html | Criacao | Macros reutilizaveis de botao/badge/card | v1 |
| 2025-11-13T17:50:48Z | src/interfaces/web/templates/theme_preview.html | Criacao | Pagina de preview do tema com tokens e componentes | v1 |
| 2025-11-13T17:50:48Z | src/interfaces/http/app.py | Atualizacao | Rota /ui/theme-preview e agregacoes p/ painel | v14 |
| 2025-11-13T17:50:48Z | src/interfaces/web/static/styles.css | Atualizacao | Classes genericas (card, token-grid) p/ design system | v10 |
| 2025-11-13T17:50:48Z | tests/integration/test_http_api.py | Atualizacao | Testar rota theme preview | v9 |
| 2025-11-13T18:05:42Z | src/interfaces/web/static/app.js | Atualizacao | Implementar toasts, refresh de logs e loader JS | v2 |
| 2025-11-13T18:05:42Z | src/interfaces/web/static/styles.css | Atualizacao | Estilos para toast, cards gen�ricos, token-grid | v11 |
| 2025-11-13T18:05:42Z | src/interfaces/web/templates/base.html | Atualizacao | Menu com link para preview do tema | v7 |
| 2025-11-13T18:05:42Z | src/interfaces/web/templates/components/ui_macros.html | Criacao | Macros UI para butoes/badges/cards | v1 |
| 2025-11-13T18:05:42Z | src/interfaces/web/templates/theme_preview.html | Criacao | P�gina demonstrando tokens/ componentes | v1 |
| 2025-11-13T18:05:42Z | tests/integration/test_http_api.py | Atualizacao | Cobrir rota de preview do tema | v10 |
| 2025-11-13T17:02:41Z | src/interfaces/http/app.py | Atualizacao | Padronizar payload de flash messages (texto+variant) para toasts | v15 |
| 2025-11-13T17:02:41Z | src/interfaces/web/templates/base.html | Atualizacao | Remover body duplicado e incluir modal global de pr�-visualiza��o | v8 |
| 2025-11-13T17:02:41Z | src/interfaces/web/templates/jobs.html | Atualizacao | Habilitar skeleton controlado por filtros e toasts com variantes | v7 |
| 2025-11-13T17:02:41Z | src/interfaces/web/templates/job_detail.html | Recriacao | Reescrever template com preview inline de artefatos e mensagens ricas | v12 |
| 2025-11-13T17:02:41Z | src/interfaces/web/static/styles.css | Atualizacao | Novos estilos para modal, artifact list, toast variants e skeleton state | v12 |
| 2025-11-13T17:02:41Z | src/interfaces/web/static/app.js | Atualizacao | Bindar skeleton triggers, modal preview e toasts parametrizados | v3 |
| 2025-11-13T17:13:04Z | src/interfaces/http/app.py | Atualizacao | Expor endpoint /api/dashboard/summary com resumo em tempo real | v16 |
| 2025-11-13T17:13:04Z | src/interfaces/web/templates/jobs.html | Atualizacao | Vincular summary grid ao endpoint vivo e exibir status de atualiza��o | v8 |
| 2025-11-13T17:13:04Z | src/interfaces/web/static/app.js | Atualizacao | Incluir bindLiveSummary com polling controlado e status visual | v4 |
| 2025-11-13T17:13:04Z | src/interfaces/web/static/styles.css | Atualizacao | Estilizar meta do resumo e estados success/error | v13 |
| 2025-11-13T17:13:04Z | tests/integration/test_http_api.py | Atualizacao | Generalizar stubs e testar API de resumo | v11 |
| 2025-11-13T17:13:04Z | tests/performance/test_http_performance.py | Atualizacao | Adaptar stub para nova assinatura e manter benchmark | v4 |
| 2025-11-13T17:30:21Z | src/domain/ports/repositories.py | Atualizacao | Adicionar contrato list_recent ao LogRepository | v5 |
| 2025-11-13T17:30:21Z | src/infrastructure/database/log_repository.py | Atualizacao | Implementar list_recent com ordenacao por timestamp | v6 |
| 2025-11-13T17:30:21Z | src/interfaces/http/dependencies.py | Recriacao | Restaurar dependencias HTTP e anexar session_id no retorno | v2 |
| 2025-11-13T17:30:21Z | src/interfaces/http/app.py | Atualizacao | Header consciente de sessao + APIs /api/dashboard/{summary,incidents} e helper de incidentes | v17 |
| 2025-11-13T17:30:21Z | src/interfaces/web/templates/base.html | Atualizacao | Exibir indicador de sessao com avatar e remover link duplicado | v9 |
| 2025-11-13T17:30:21Z | src/interfaces/web/templates/jobs.html | Atualizacao | Adicionar painel de incidentes vivo e meta de resumo | v9 |
| 2025-11-13T17:30:21Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Propagar header_session e ajustar badges para uppercase | v13 |
| 2025-11-13T17:30:21Z | src/interfaces/web/static/styles.css | Atualizacao | Estilizar indicador de sessao e painel de incidentes responsivo | v14 |
| 2025-11-13T17:30:21Z | src/interfaces/web/static/app.js | Atualizacao | Polling de resumo/incidentes e sessao de skeletons unificada | v5 |
| 2025-11-13T17:30:21Z | tests/integration/test_http_api.py | Atualizacao | Cobrir APIs de resumo/incidentes e stubs multi-job/log | v12 |
| 2025-11-13T17:30:21Z | tests/performance/test_http_performance.py | Atualizacao | Ajustar stub para nova assinatura de repositorio | v5 |
| 2025-11-13T17:30:21Z | tests/unit/domain/test_register_delivery.py | Atualizacao | Repositorio em memoria suporta list_recent para logs | v2 |
| 2025-11-13T17:30:21Z | tests/unit/domain/test_create_job.py | Atualizacao | Stubs expostos aderem ao novo contrato do LogRepository | v2 |
| 2025-11-13T17:30:21Z | tests/integration/test_pipeline_and_review.py | Atualizacao | Repositorio de logs em memoria implementa list_recent | v5 |
| 2025-11-13T17:30:21Z | tests/support/stubs.py | Atualizacao | MemoryLogRepository passa a expor list_recent para incidentes | v2 |
| 2025-11-13T17:30:21Z | tests/support/domain.py | Atualizacao | LogRepositorySpy compatibilizado com list_recent | v2 |
| 2025-11-14T12:38:48Z | src/application/services/accuracy_service.py | Atualizacao | Adicionar avaliacao WER/penalidades para atingir meta de 99% | v2 |
| 2025-11-14T12:38:48Z | tests/unit/application/test_accuracy_service.py | Atualizacao | Atualizar cenarios para novo guard e garantir metadados coerentes | v2 |
| 2025-11-14T12:46:19Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Expor painel de acuracia por job | v3 |
| 2025-11-14T12:46:19Z | src/interfaces/web/templates/jobs.html | Atualizacao | Adicionar filtro/coluna de precisao | v3 |
| 2025-11-14T12:46:19Z | src/interfaces/http/app.py | Atualizacao | Suportar filtro accuracy e repassar snapshot ao template | v3 |
| 2025-11-14T12:46:19Z | src/application/services/accuracy_service.py | Atualizacao | Calculo WER com referencias e telemetria | v3 |
| 2025-11-14T12:46:19Z | src/infrastructure/container/service_container.py | Atualizacao | Registrar loader de referencia e dispatchers | v3 |
| 2025-11-14T12:46:19Z | scripts/report_accuracy_metrics.py | Criacao | Relatorio de metrica de acuracia alimentado por logs | v1 |
| 2025-11-14T12:46:19Z | docs/accuracy_metrics_summary.md | Atualizacao | Snapshot mais recente das avaliacoes de acuracia | v1 |
| 2025-11-14T12:48:50Z | profiles/references/geral.txt | Criacao | Registrar referencia aprovada para perfil geral | v1 |
| 2025-11-14T12:48:50Z | processing/jobs.json | Atualizacao | Exemplo de job com metadata de acuracia para QA manual | v1 |
| 2025-11-14T12:49:43Z | docs/accuracy_metrics_summary.md | Atualizacao | Regenerar snapshot via script de telemetria | v2 |
| 2025-11-14T12:59:32Z | config/runtime_credentials.py | Atualizacao | Exigir secret e recriptografar automaticamente o cofre | v2 |
| 2025-11-14T12:59:32Z | .env.example | Atualizacao | Documentar CREDENTIALS_SECRET_KEY obrigatoria | v2 |
| 2025-11-14T12:59:32Z | tests/unit/config/test_runtime_credentials.py | Atualizacao | Ajustar cobertura para novo comportamento seguro | v2 |
| 2025-11-14T13:18:02Z | src/interfaces/http/dependencies.py | Atualizacao | Converter require_active_session para async com valida??o CSRF e g??nero de tokens | v2 |
| 2025-11-14T13:18:02Z | src/application/services/session_service.py | Atualizacao | Incluir emiss?o persistente de csrf_token por sess??o | v2 |
| 2025-11-14T13:18:02Z | src/interfaces/web/templates/base.html | Atualizacao | Injetar meta csrf_token global para scripts | v2 |
| 2025-11-14T13:18:02Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Inserir tokens CSRF em formul??rios cr??ticos e mostrar badges | v3 |
| 2025-11-14T13:18:02Z | src/interfaces/web/templates/api_settings.html | Atualizacao | Formularios agora enviam csrf_token | v2 |
| 2025-11-14T13:18:02Z | src/interfaces/web/templates/template_settings.html | Atualizacao | Incluir CSRF nos formul??rios de template e modal | v2 |
| 2025-11-14T13:18:02Z | src/interfaces/web/static/js/core.js | Atualizacao | Adicionar helpers getCsrf/withCsrf para fetch | v2 |
| 2025-11-14T13:18:02Z | src/interfaces/web/static/js/jobs.js | Atualizacao | Propagar header X-CSRF-Token nos POSTs via fetch | v2 |
| 2025-11-14T13:18:02Z | src/interfaces/web/static/js/settings.js | Atualizacao | Propagar CSRF em formul??rios AJAX/DELETE/preview | v2 |
| 2025-11-14T13:18:02Z | src/interfaces/http/app.py | Atualizacao | Contextos com csrf_token, enforce rate limit e assinaturas em downloads | v3 |
| 2025-11-14T13:18:02Z | config/feature_flags.json | Atualizacao | Adicionar flag downloads.signature_required (default true) | v2 |
| 2025-11-14T13:18:02Z | tests/integration/test_http_api.py | Atualizacao | Incluir tokens CSRF nos overrides e assinaturas de download nos testes | v3 |
| 2025-11-14T13:22:17Z | src/infrastructure/container/service_container.py | Atualizacao | Cache de referencias aprovadas por perfil e suporte a overrides | v2 |
| 2025-11-14T13:22:17Z | scripts/report_accuracy_metrics.py | Atualizacao | Leitura streaming com limite maximo para evitar OOM | v2 |
| 2025-11-14T13:22:17Z | docs/accuracy_metrics_summary.md | Atualizacao | Regenerado apos otimizacao de script | v2 |
| 2025-11-14T13:30:51Z | src/infrastructure/telemetry/metrics_logger.py | Atualizacao | Enviar metricas/alertas opcionalmente para webhooks e manter log local | v2 |
| 2025-11-14T13:30:51Z | .env.example | Atualizacao | Documentar ALERT_WEBHOOK_URL e METRICS_WEBHOOK_URL | v3 |
| 2025-11-14T13:30:51Z | config/settings.py | Atualizacao | Expor campos alert_webhook_url/metrics_webhook_url | v2 |
| 2025-11-14T13:34:32Z | .github/workflows/ci.yml | Atualizacao | Injecao de secrets, pip-audit e envs coerentes no pipeline CI | v2 |
| 2025-11-14T13:37:24Z | src/interfaces/http/app.py | Atualizacao | Expor resumo de precisao via API/HTML e contexto com accuracy_summary | v4 |
| 2025-11-14T13:37:24Z | src/interfaces/web/templates/jobs.html | Atualizacao | Cards adicionais com media e contagem de precisao | v3 |
| 2025-11-14T13:37:24Z | src/interfaces/http/app.py | Atualizacao | Helper _compute_accuracy_summary e API dashboard estendida | v5 |
| 2025-11-14T13:37:24Z | .github/workflows/ci.yml | Atualizacao | Novo job reports que gera/upload accuracy_metrics_summary.md | v3 |
| 2025-11-14T13:41:07Z | src/interfaces/web/templates/jobs.html | Atualizacao | Melhorar comunicacao dos cards de precisao e fallback amigavel | v4 |
| 2025-11-14T13:41:07Z | src/interfaces/web/templates/job_detail.html | Atualizacao | Mensagem amigavel para descricoes de template | v4 |
| 2025-11-14T13:41:07Z | config/runtime_credentials.json | Regenerado | Recriado com payload ficticio apos limpeza | v2 |
| 2025-11-14T13:51:11Z | src/interfaces/web/templates/jobs.html | Atualizacao | Legendas acessiveis, escopos e integracao com live accuracy cards | v5 |
| 2025-11-14T13:51:11Z | src/interfaces/web/templates/template_settings.html | Atualizacao | Tabela com caption e scopes para acessibilidade | v3 |
| 2025-11-14T13:51:11Z | src/interfaces/web/static/styles.css | Atualizacao | Classe sr-only para suportar legendas ocultas | v2 |
| 2025-11-14T13:51:11Z | src/interfaces/web/static/js/dashboard.js | Atualizacao | Atualizar cards de precisao via payload.accuracy | v3 |
| 2025-11-14T13:51:11Z | config/runtime_credentials.json | Regenerado | Limpeza e rebootstrap do store cifrado | v3 |
| 2025-11-14T14:05:35Z | DEPLOYMENT.md | Criacao | Documentar prerequisitos e passos formais de deploy | v1 |
| 2025-11-14T14:05:35Z | .env.production.example | Criacao | Modelo de variaveis para staging/producao | v1 |
| 2025-11-14T13:58:42Z | tests/unit/application/test_session_service.py | Criacao | Cobrir lifecycle do SessionService e tokens CSRF | v1 |
| 2025-11-14T13:59:32Z | tests/unit/infrastructure/test_metrics_logger.py | Criacao | Validar m�tricas/alertas e script de relat�rio | v1 |

| 2025-11-14T14:05:10Z | tests/unit/infrastructure/test_file_job_repository.py | Criacao | Repositorio de jobs em arquivo com ordenacao/atualizacao | v1 |
| 2025-11-14T14:06:45Z | tests/unit/infrastructure/test_components_asr.py | Criacao | Cobrir build_core_usecases e clientes ASR | v1 |

| 2025-11-14T14:12:20Z | tests/unit/application/test_job_controller.py | Criacao | Cobrir list/ingest/process/requeue do JobController | v1 |
| 2025-11-14T14:13:55Z | tests/unit/application/test_review_controller.py | Criacao | Revis�o com entrega e erros | v1 |
| 2025-11-14T14:15:30Z | tests/unit/interfaces/cli/test_run_job_cli.py | Criacao | Fluxos de CLI run_job | v1 |
| 2025-11-14T14:17:05Z | tests/unit/interfaces/cli/test_watch_inbox.py | Criacao | Handler da caixa de entrada em diferentes cen�rios | v1 |

| 2025-11-14T14:20:11Z | tests/unit/interfaces/http/test_app_helpers.py | Criacao | Cobrir agregadores de precisao e rate limit | v1 |
| 2025-11-14T14:20:45Z | tests/integration/test_http_api.py | Atualizacao | Novos testes para summary de precisao e limitador | v4 |

| 2025-11-14T14:25:11Z | tests/unit/application/test_logging_and_templates.py | Criacao | Cobrir logging_config, templates e audio chunker | v1 |

