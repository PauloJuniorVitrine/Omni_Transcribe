# Interface Diagnóstico — EXEC_ID 20251113T103533Z_MSJTU6

## Visão Geral
- Stack atual: FastAPI + templates Jinja2, CSS simples em `/static/styles.css`.
- Navegação: `/` (lista), `/jobs/{id}` (detalhe), formulários de review/processo, downloads e login via OAuth redirect.
- Não há SPA, router JS ou stores; toda lógica é server-rendered.

## Componentes Existentes
| Tela | Componentes | Observações |
|------|-------------|-------------|
| Dashboard (`jobs.html`) | Tabela, estado vazio, link para detalhes | Falta filtros, busca, paginação visual |
| Detalhe (`job_detail.html`) | Metadados, lista de artefatos, preview, formulários de review/processo | Sem indicadores de progresso nem cards resumidos |
| Header (`base.html`) | Logo textual, nav (Jobs, Entrar) | Não há branding visual nem toggle logout |

## UX Diagnostics
- **Feedback**: Flashes recém-implementados cobrem review/process/download/login, mas não há loading indicators.
- **Acessibilidade**: Layout simples; falta contraste/dark mode/ARIA.
- **Segurança visual**: Ações críticas (reprocessar) não exigem confirmação; downloads abrem direto.
- **Responsividade**: CSS atual não garante mobile (tabela fixa).
- **Estética**: Sem design tokens, sem logotipo, tipografia padrão.

## Riscos Identificados
- Usuário pode clicar “Iniciar processamento” repetidas vezes sem confirmação → duplicidade.
- Falta alerta de sessão expirada; quando cookie vence, UI volta para login silenciosamente.
- Download sem previsualização pode expor caminhos caso seja acessado via URL manual.

## Cobertura x Backend
- Endpoints técnicos (`/api/jobs/...`, `/webhooks`) não aparecem na interface pública, conforme esperado.
- Falta visualização para logs/artefatos adicionais (SRT/VTT listados mas não preview).

