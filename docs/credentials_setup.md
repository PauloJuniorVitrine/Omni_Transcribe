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

4. **Executando o instalador com segurança**
   Use os wrappers `scripts/run_transcribeflow.bat` (Windows) ou `scripts/run_transcribeflow.ps1` para garantir que a variável esteja definida antes de iniciar `TranscribeFlow.exe`. Eles validam o segredo e exibem um aviso amigável se faltar.

5. **Testes automatizados**
   Há um teste que valida o script de geração de credenciais: `pytest tests/unit/scripts/test_generate_runtime_credentials.py`. Ele garante que o arquivo é criado com a chave adequada e que a execução falha quando o segredo não existe.
