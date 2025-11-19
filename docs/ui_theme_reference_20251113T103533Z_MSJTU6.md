# UI Theme Reference — EXEC_ID 20251113T103533Z_MSJTU6

## Tokens (theme.css)
| Token | Valor | Uso |
|-------|-------|-----|
| `--color-bg` | #f5f7fb | Fundo geral |
| `--color-surface` | #ffffff | Cards/sections |
| `--color-header` | #0f172a | Header(nav) |
| `--color-header-text` | #ffffff | Texto header |
| `--color-primary` | #2563eb | Botões, flashes |
| `--color-secondary` | #f97316 | Ações secundárias |
| `--color-text` | #111827 | Texto padrão |
| `--color-text-muted` | #6b7280 | Labels |
| `--color-border` | #e5e7eb | Bordas/tabelas |
| `--color-success` | #16a34a | Badges sucesso |
| `--color-warning` | #f59e0b | Timeline warning |
| `--color-danger` | #dc2626 | Timeline error |
| `--radius-*` | 4/6/10px | Bordas cards/botões |
| `--shadow-*` | sm/md | Elevação |
| `--font-base` | Inter/Segoe | Tipografia |

## Aplicação Atual
- Dashboard usa `summary-card`, `filters`, `table` responsivo.
- Header + branding reutilizam tokens (gradiente primary→secondary).
- Timeline, flashes, botões herdam classes `.btn`, `.badge`.

## Próximos Passos
1. Criar variante dark mode (usar `prefers-color-scheme`).
2. Extrair componentes (botão, card, badge) para partials reutilizáveis em `_includes` Jinja.
3. Documentar tokens no README/UI.
## Modo escuro
- Habilitado automaticamente via `prefers-color-scheme` (tokens redefinidos em `theme.css`).
- Elementos (cards, header, badges) respeitam tokens; não é necessário classe adicional.

## Componentes Base
| Componente | Classe | Descrição |
|-----------|--------|-----------|
| Botão primário | `.btn.btn-primary` | Usa `--color-primary`, sombra e animação hover |
| Botão secundário | `.btn.btn-secondary` | Usa `--color-secondary` |
| Badge | `.badge`, `.badge-INFO/WARNING/ERROR` | Cores derivadas de tokens + ícones |
| Card resumo | `.summary-card` | Gradiente header + shadow-md |
| Timeline | `.timeline`, `.timeline-item` | Estrutura vertical com ícones e ações |

## Painel de incidentes
- Exibe eventos dos últimos 5 logs críticos (`has_more` indica backlog).
- Usa classes `.critical-card`, `.badge-WARNING/ERROR`.

## Como expandir
1. Para novos componentes, adicione tokens no `theme.css` e doc no Markdown.
2. Use partials Jinja em `templates/components/` para compartilhar header/card.
3. Planeje Storybook real quando migrarmos para React.
