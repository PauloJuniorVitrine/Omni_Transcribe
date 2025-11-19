# Interface Proposta — EXEC_ID 20251113T103533Z_MSJTU6

## 1. Dashboard (SaaS-style)
- **Layout**: grid responsivo com cards superiores (Total jobs, Aguardando revisão, Falhas recentes) e tabela filtrável abaixo.
- **Interações**:
  - Busca instantânea por ID/arquivo.
  - Filtros por status/perfil/engine (chips). 
  - Botão “Criar job manual” (se aplicável) e “Atualizar” com indicador de sync.
- **Feedback**: skeleton enquanto carrega; badges coloridos (verde aprovado, amarelo aguardando, vermelho falhou).
- **Roteamento**: `/jobs/{id}` via click no card ou linha.

## 2. Detalhe do Job
- **Header**: card resumido com status, perfil, idioma, duração, actions (Processar novamente, Baixar pacote, Ver logs).
- **Abas/Seções**:
  1. **Transcrição**: preview com highlight, botão “Copiar”.
  2. **Artefatos**: cards para TXT/SRT/VTT/JSON/ZIP com ações (download, ver em modal, share link).
  3. **Revisão**: formulário com campos pré-validados, histórico de revisões recentes.
  4. **Logs & Eventos**: timeline com registros (delivery, erros, webhook).
- **Feedback**: loader/estado “Processando…” com progress indicator (polling) e toasts para status.

## 3. Autenticação & Sessão
- Adicionar avatar/menu no header com estado da sessão, botão “Logout” e info do usuário.
- Modal informando expiração iminente da sessão (cookie TTL) com CTA “renovar”.

## 4. Segurança Visual
- Ações críticas (reprocessar, excluir artefatos) pedem confirmação modal + resumo do impacto.
- Flash message aumenta, mas também adicionar toast persistente e log no painel “Notificações”.

## 5. Responsividade
- Tabela vira cards empilhados em mobile.
- Botões de ação agrupados em “kebab menu” em telas pequenas.

## 6. Design System (alto nível)
- Cores inspiradas em Stripe (azul/roxo) e Supabase (cards com leve sombra).
- Tipografia: Inter / Source Sans, 14-16px base.
- Componentes reutilizáveis: `Badge`, `Card`, `Button`, `Toast`, `Modal`, `ListItem`.

## 7. Export / Prototipação
- Estrutura pronta para Storybook (cards, tabela, formulário) e import em Figma.
- Cada componente documentado com props (status, label, icon).

