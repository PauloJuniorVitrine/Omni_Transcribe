# Frontend Tooling Plan – ES Modules (IMP-003 follow-up)

## Objetivo
Habilitar lint/testes para `src/interfaces/web/static/js/*` garantindo qualidade e CI automatizável.

## Etapas
1. **Provisionar ambiente npm**  
   - Pré-requisito: Node.js ≥ 20.  
   - Instalar `npm` no host local ou configurar container/tooling (ex.: `node:20-bullseye`).  
   - Validar com `node -v` e `npm -v`.

2. **Inicializar projeto**  
   ```bash
   npm init -y
   npm install --save-dev eslint prettier jest @babel/preset-env
   ```
   - Estrutura sugerida:
     ```
     package.json
     /scripts
       └─ lint-frontend.js (opcional)
     ```

3. **Configurar ESLint + Prettier**  
   - `.eslintrc.cjs` com parser `babel-eslint` e env `browser`, `es2020`.  
   - Regras principais: `no-unused-vars`, `no-undef`, `semi: ["error", "always"]`.

4. **Adicionar testes**  
   - Criar `tests/frontend/` com Jest + JSDOM para cobrir:
     - `jobs.js`: fetch de logs (mockar `fetch`).  
     - `settings.js`: submissão AJAX.  
     - `dashboard.js`: polling e update de labels.

5. **Atualizar CI**  
   - Scripts no `package.json`:
     ```json
     {
       "scripts": {
         "lint:js": "eslint src/interfaces/web/static/js",
         "test:js": "jest"
       }
     }
     ```
   - No pipeline: executar `npm run lint:js && npm run test:js` antes de `pytest`.

6. **Documentar**  
   - Atualizar README/CHANGE_SUMMARY reforçando que ambientes de dev precisam do tooling Node.

## Status atual
- Ambiente local (CLI) **não possui npm** → pendente até que seja instalado ou executado em CI.  
- Após provisionamento, seguir etapas acima e registrar resultados em `docs/test_validation_{EXEC_ID}.md`.

## Dependências / Próximos Passos
1. Alocar ambiente com Node >= 20 (ex.: container `node:20-bullseye` ou workstation dev).  
2. Executar `npm init -y` na raiz, instalar dependências e confirmar que `npm run lint:js && npm run test:js` passa.  
3. Atualizar checklist `ajustes_finais.md` quando o tooling estiver disponível e os scripts configurados.
