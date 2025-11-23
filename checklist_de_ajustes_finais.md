# Checklist de Ajustes Finais (ordenado por criticidade)

- [x] Corrigir path traversal no upload: sanitizar `file.filename` (basename/slug ou UUID), bloquear `..`/separadores e validar extensao antes de gravar; retestar upload/auto_process.
- [x] Garantir assinatura obrigatoria para downloads: incluir `downloads.signature_required` no default ou falhar start se `feature_flags.json` ausente/corrompido; validar links assinados no dashboard.
- [x] Atualizar documentacao oficial (DEV/DEPLOYMENT) para refletir acuracia guard, OAuth/CSRF, flags e expectativas de seguranca; remover ou confidenciar docs datados em `docs/`.
- [x] Adicionar smoke real pre-release: fluxo upload -> process -> download com backend real (nao stub) em pipeline ou checklist manual antes de build_exe/installer. (Script helper: `scripts/smoke_pipeline_stub.py` valida wiring com stubs; pipeline pode rodar `python scripts/smoke_pipeline_stub.py` como gate rapido. Instrucoes adicionais no DEV_GUIDE e `docs/smoke_real.md`.)
- [x] Harden OAuth/sessao: validar `state` obrigatorio, tratar falhas de IO do store com alerta, limitar duracao/tamanho e garantir cookies `Secure`/`SameSite` em producao.
- [x] Melhorar observabilidade: incluir trace_id/correlacao nos logs principais e nas metricas/alertas; padronizar campos (event/job_id).
- [x] Endurecer upload: limitar tamanho por perfil, checar MIME, limpar nomes, bloquear tipos suspeitos e manter chunking seguro.
- [x] Reavaliar persistencia: migrar de JSON/filelock para backend mais robusto (SQLite/Postgres) ou cache para listagem de jobs sob concorrencia. (Plano detalhado em `docs/persistence_migration_plan.md`; backend SQLite opcional implementado.)
- [x] Refined rate-limit/quotas: persistir ou adicionar limites por IP/usuario para downloads/APIs, nao apenas sessao em memoria.
- [x] Seguranca HTTP: garantir HSTS/CSP no proxy, CORS restrito em producao, headers e cookies `Secure`/`SameSite`.
- [x] Testes: manter suites completas verdes (unit, integration, frontend, e2e, performance) cobrindo download assinado e upload sanitizado; reforcar contratos OpenAPI.

## 📐 CoCoT (Comprovacao, Causalidade, Contexto, Tendencia)
- Comprovacao: aderir a OWASP (upload sanitizado, CSRF, CORS), NIST para storage seguro e boas praticas FastAPI para validacao.
- Causalidade: uploads sem sanitizacao permitem escrita arbitraria; flag de assinatura ausente expõe artefatos; doc desatualizada induz configuracao insegura.
- Contexto: arquitetura file-based + FastAPI; sessoes OAuth/CSRF; dashboards com downloads assinados; CI com Playwright stub.
- Tendencia: incorporar tracing distribuido, headers de seguranca no proxy, storage robusto (SQLite/Postgres) e contratos OpenAPI com tipagem gerada no frontend.

## 🌲 ToT (Tree of Thought)
- Upload seguro: 1) normalizar nome -> 2) validar extensao/MIME -> 3) gravar em dir sandbox -> 4) testar fluxo end-to-end.
- Downloads: 1) default flag true -> 2) fallback fail-fast -> 3) teste de assinatura -> 4) monitorar metricas de acesso.
- Observabilidade: 1) definir trace_id -> 2) propagar em logs/métricas -> 3) visualizar em painéis -> 4) revisar alertas.
- Persistencia: 1) manter JSON atual? 2) migrar para SQLite? 3) adotar Postgres em HA? Escolher conforme carga/concorrencia.

## ♻️ ReAct – Simulacao e Reflexao
- Upload sanitizado: aplicando slug/UUID elimina traversal; impacto: nomes menos legiveis, mitigado com metadata original; risco mitigado de escrita fora do inbox.
- Flag de assinatura default: falha ao subir se ausente evita downloads abertos; risco: impedir start em dev -> mitigar com flag explicita TEST_MODE.
- Trace_id em logs: adiciona campo em eventos/alertas; custo baixo, aumenta rastreabilidade em incidentes.

## 🖼️ Representacoes Visuais (sugeridas)
- Diagrama de fluxo upload->process->artefatos->download (com pontos de validacao/assinatura/CSRF).
- Mapa de modulos: domain/usecases ↔ application/services ↔ infrastructure/container/api ↔ interfaces/http/web/js.
- Diagrama de entidades: Job, Artifact, Profile, LogEntry, UserReview, DeliveryRecord e relacoes com repositorios JSON/CSV.
