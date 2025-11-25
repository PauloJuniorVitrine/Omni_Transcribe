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
- O `package.json` já define toda a cadeia npm (ESLint, Jest, geração de OpenAPI/TS) e está incluído no pipeline principal (`npm run lint:js`, `npm run test:js`, `npm run typecheck:contracts`, `npm run test:e2e`).  
- A suíte de testes em `tests/frontend/*.test.js` já cobre `jobs.js`, `settings.js`, `dashboard.js` e outros módulos estáticos; basta instalar as dependências (`node 20`, `npm ci`) e executar os scripts citados.  
- Ao rodar localmente, confirme `node -v`/`npm -v`, execute `npm ci`, depois `npm run lint:js && npm run test:js -- --runInBand --ci` para validar o front-end antes de qualquer deploy.

## Dependências / Próximos Passos
1. Alocar ambiente com Node >= 20 (ex.: container `node:20-bullseye` ou workstation dev).  
2. Executar `npm init -y` na raiz, instalar dependências e confirmar que `npm run lint:js && npm run test:js` passa.  
3. Atualizar checklist `ajustes_finais.md` quando o tooling estiver disponível e os scripts configurados.
