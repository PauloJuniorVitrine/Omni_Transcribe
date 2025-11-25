# Arquitetura & Fluxos principais

Este documento expõe a visão geral exigida: o pipeline de ingestão de áudio, os módulos que compõem o domínio e onde cada responsabilidade vive no repositório.

## 1. Fluxo de processamento (Watchers → Controllers → Pipeline → Artefatos)

```mermaid
flowchart LR
    W(Watcher / `scripts/watch_inbox.py`)
    JC(JobController)
    P(ProcessJobPipeline)
    R(Repositories / Artefatos)
    A(Artifacts / Storage)
    LOG(LogRepository / Observability)

    subgraph Pipeline[""]
        RunASR[RunAsrPipeline]
        PostEdit[PostEditTranscript]
        Generate[GenerateArtifacts]
    end

    W -->|Cria job| JC
    JC --> P
    P --> RunASR --> PostEdit --> Generate --> A
    Generate --> R
    P --> LOG
    LOG -->|Retries & decisões| P
```

## 2. Mapa de diretórios principais

- `src/application` – controladores e serviços que expõem os casos de uso (job controladores, inserções, geração de artefatos, serviços de logging/telemetria).
- `src/domain` – entidades (`Job`, `Artifact`, `Transcription`), value objects e casos de uso (`CreateJob`, `RunAsr`, `ProcessJobPipeline`, `RetryOrReject`).
- `src/infrastructure` – integrações com APIs externas (OpenAI, GoTranscript), persistência (`storage`, `sqlite`), container de serviços e telemetria.
- `src/interfaces/http` – FastAPI com rotas web + APIs, templates Jinja e dependências que materializam o `JobController` e `ReviewController`.
- `src/interfaces/cli` – scripts de linha de comando (watcher, run_job) que acionam os casos de uso de forma batch/assincrona.
- `src/interfaces/web` – recursos estáticos, templates e componentes usados pelo dashboard.
- `scripts/` – utilitários de build (PyInstaller, NSIS), geração de schemas/credentials e stubs de teste.
- `config/` – configuração central (settings, feature flags, runtime credentials) usada pelo container de serviços em `infrastructure/container`.

## 3. Relações entre módulos-chave

- `JobController` (no `application`) orquestra `CreateJobFromInbox`, `ProcessJobPipeline` e `RetryOrRejectJob` conectando `JobRepository` e `LogRepository`.
- `RunAsrPipeline` usa `JobRepository`, `ProfileProvider`, `AsrService` e `LogRepository` para avançar o status do job e emitir eventos.
- Os serviços em `infrastructure/container` expõem instâncias configuradas (timing, feature flags, providers) para as interfaces HTTP/CLI e para a pipeline.
- A telemetria (`infrastructure/telemetry/metrics_logger.py`) registra métricas de downloads e tabelas de incidentes consultadas pelo dashboard FastAPI.

## 4. Como usar este guia

Este documento e `docs/visualizations.md` devem caminhar juntos: sempre que uma mudança tocar controllers, pipeline ou watchers, atualize ambos (diagrama/descrições + representações visuais) mantendo a abordagem CoCoT/ToT/ReAct em mente.

## 5. Observabilidade e métricas

- Métricas escritas em `logs/metrics.log` pelo `infrastructure.telemetry.metrics_logger` incluem:
  - `pipeline.stage.duration`: latência de cada etapa (`asr`, `post_edit`, `artifacts`) com sucesso/erro.
  - `pipeline.asr.completed`: dados do resultado ASR (engine, idioma, chunk_count, chunked).
  - `pipeline.artifacts.generated`: quantidade/tipos de artefatos criados.
  - `pipeline.completed`: confirmação de pipeline inteiro finalizado.
  - `pipeline.retry.triggered`: tentativas adicionais quando `RetryOrRejectJob` requeueia um job.
  - `pipeline.failed` (alerta) disparado via `notify_alert` para decorar falhas de estágio com contexto.
- Alerts são registrados em `logs/alerts.log` e podem disparar webhooks registrados nas variáveis `ALERT_WEBHOOK_URL`/`METRICS_WEBHOOK_URL`.
- O novo arquivo `logs/metrics_histograms.json` armazena buckets agregados para latências (`pipeline.stage.latency`) e chunk counts (`pipeline.asr.chunk_count`), permitindo análise offline das distribuições sob carga e reforçando a comprovação CoCoT do comportamento escalar.
- A lógica de qualidade (`TranscriptionAccuracyGuard`) dispara `notify_alert` com o evento `accuracy.guard.alert` sempre que um job precisa de revisão (`accuracy_requires_review=true`), entregando payload com `wer` e `score` diretamente para webhooks/email e garantindo alertas automáticos para as equipes de revisão.

## 6. Interface interativa

- Os filtros do dashboard agora consomem `GET /api/dashboard/jobs`, que expõe o mesmo passo de paginação/filters (`status`, `profile`, `accuracy`, `limit`, `page`) usado na interface tradicional e retorna as listas, os cards de summary e o timestamp (`generated_at`). O JavaScript `src/interfaces/web/static/js/jobs.js` usa essa rota para atualizar tabela, cards e controles de paginação sem reload, mantendo a abordagem de ToT (múltiplos caminhos avaliados) e ReAct (simular impacto antes de renderizar).
- A renderização reativa inclui badges de status (`badge-WARNING`, `badge-success`, `badge-INFO`, `badge-danger`) e sinaliza `accuracy_requires_review` para destacar jobs que precisam de auditoria, dificultando a passagem de casos com saúde degradada.
- O painel de preview de templates acessa `GET /api/templates/preview` com `_build_preview_context`, permitindo validar instantaneamente os templates de entrega sem submeter jobs reais e reforçando a comprovação técnica (CoCoT) das escolhas de template.
- O novo endpoint `POST /api/uploads` aceita tokens assinados (`/api/uploads/token`) para persistir arquivos de áudio e disparar o pipeline sem depender da interface tradicional; tokens têm TTL curto e estão atrelados a perfil/engine, que facilita integrações externas seguras.
