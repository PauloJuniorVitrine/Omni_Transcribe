# CI/CD Secrets Policy

1. **Variáveis obrigatórias**  
   - `CREDENTIALS_SECRET_KEY` (base64 url-safe, 32 bytes).  
   - `WEBHOOK_SECRET` (já existente, usado também em download tokens).  
   - CI deve falhar se alguma dessas env vars estiver vazia nas pipelines de build/deploy.

2. **Implementação sugerida**  
   ```bash
   # Exemplo GitHub Actions
   - name: Validate secrets
     run: |
       test -n "$CREDENTIALS_SECRET_KEY" || (echo "Missing CREDENTIALS_SECRET_KEY" && exit 1)
       test -n "$WEBHOOK_SECRET" || (echo "Missing WEBHOOK_SECRET" && exit 1)
   ```

3. **Documentação**  
   - Adicionar seção no README/CHANGE_SUMMARY indicando que o runtime store agora exige a env.  
   - Em ambientes locais, gerar chave com:
     ```bash
     python - <<'PY'
     import base64, os
     print(base64.urlsafe_b64encode(os.urandom(32)).decode())
     PY
     ```

4. **Rotação**  
   - Atualizar `CREDENTIALS_SECRET_KEY` pela pipeline e recriptografar `config/runtime_credentials.json`.  
   - Registrar a rotação em `config/runtime_credentials_audit.log`.
