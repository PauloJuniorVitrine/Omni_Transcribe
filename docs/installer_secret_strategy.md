## Estratégia de segredo para instaladores

1. **Ambientes controlados (GitHub Actions / servidores corporativos)**
   - Defina `CREDENTIALS_SECRET_KEY` ou `RUNTIME_CREDENTIALS_KEY` no pipeline com o valor do secret cadastrado no repositório.
   - Ao iniciar `TranscribeFlow.exe` ou os scripts (`scripts/run_job.py`, `scripts/watch_inbox.py`), o `RuntimeCredentialStore` prioriza essa variável (veja `config/runtime_credentials.py:71-151`).
   - Com o env var carregado, o arquivo `config/.credentials_secret.key` é ignorado, fortalecendo conformidade e rotação de chaves.

2. **Ambientes autônomos (instalador distribuído)**
   - Quando não houver env var, o `RuntimeCredentialStore` gera automaticamente um segredo (`secrets.token_urlsafe(32)`) e grava em `config/.credentials_secret.key` (`config/runtime_credentials.py:52-90`).
   - Proteja esse arquivo (`.gitignore`, ACLs) e não o compartilhe; ele funciona como fallback local.
   - Para rotacionar a chave, remova `.credentials_secret.key` e reinicie o instalador; ele criará uma nova chave.

3. **Validação pós-instalação**
   - Verifique `config/runtime_credentials_audit.log` para confirmar que não há erros de cipher.
   - Caso haja falhas, remova o arquivo `.credentials_secret.key`, defina a env var e rode novamente para garantir consistência.

4. **Scripts auxiliares recomendados**
   - Crie um script de bootstrap (bash/Powershell) que:
     - Garante que `config/.credentials_secret.key` exista com `secrets.token_urlsafe(32)` quando não houver env.
     - Registra (ou mostra) a chave utilizada para referência da equipe (sem expor em logs públicos).
   - Isso ajuda a igualar o comportamento entre o instalador e o GitHub Actions, mantendo o “resultado positivo”.

Esses passos asseguram que o instalador rode com sucesso tanto em máquinas “limpas” quanto sob pipelines controlados, sem alterar a segurança do cofre criptografado.
