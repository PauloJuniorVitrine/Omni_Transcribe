# Gerando o cofre runtime com `CREDENTIALS_SECRET_KEY`

O workflow e os testes unitários dependem de `config/runtime_credentials.json` criptografado com a mesma chave (`CREDENTIALS_SECRET_KEY`) definida nos segredos do GitHub. Para gerar (ou regenerar) esse arquivo localmente:

1. **Defina a variável de ambiente**
   ```bash
   export CREDENTIALS_SECRET_KEY="sua-chave-urlsafe-32-bytes"
   ```
   No Windows PowerShell:
   ```powershell
   $env:CREDENTIALS_SECRET_KEY="sua-chave-urlsafe-32-bytes"
   ```

2. **Execute o script gerador**
   ```bash
   python scripts/generate_runtime_credentials.py
   ```
   Isso cria/atualiza `config/runtime_credentials.json` com `DEFAULT_CREDENTIALS` e criptografa com a chave atual. O mesmo script pode ser usado para recriptografar após trocar a chave.

3. **Finalize com commit**
   Se você precisa manter o arquivo no repositório para testes, coloque-o sob controle de versão _apenas depois_ de garantir que a chave usada é a mesma do ambiente de CI. É recomendável manter esse arquivo fora do git e deixá-lo regenerável na máquina de cada desenvolvedor.

4. **GitHub Actions**
   O workflow `system-validation.yml` já exporta `CREDENTIALS_SECRET_KEY` nos jobs Python, então ele lê o cofre de forma consistente. Apenas certifique-se de ter o mesmo valor nos `Secrets` do repositório.
