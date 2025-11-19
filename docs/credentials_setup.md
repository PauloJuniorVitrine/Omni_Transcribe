# Gerando o cofre runtime com `CREDENTIALS_SECRET_KEY`

Os testes unitários e o workflow dependem de `config/runtime_credentials.json` criptografado com o mesmo segredo utilizado no CI.

1. **Exporte a chave**
   ```bash
   export CREDENTIALS_SECRET_KEY="sua-chave-32-bytes"
   ```
   No PowerShell:
   ```powershell
   $env:CREDENTIALS_SECRET_KEY="sua-chave-32-bytes"
   ```

2. **Execute o script**
   ```bash
   python scripts/generate_runtime_credentials.py
   ```
   O script salva `config/runtime_credentials.json` (baseado em `DEFAULT_CREDENTIALS`) e imprime o caminho do arquivo.

3. **Não compartilhe a chave**  
   Mantenha o arquivo fora do git ou regenere-o sempre que a chave mudar. O workflow `system-validation.yml` usa a mesma variável (`CREDENTIALS_SECRET_KEY`) para descriptografar no CI.
