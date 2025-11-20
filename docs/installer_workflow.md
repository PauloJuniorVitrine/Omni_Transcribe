## Fluxo ideal para o instalador TranscribeFlow

### Objetivo
Garantir que o instalador no Windows 10/11 x64 configure o runtime, mostre progresso, crie o atalho e abra direto a interface web com zero passos manuais extras.

### Passo único automatizado
1. Atualize `scripts/install.env` (ou `.env`) com:
   ```
   OPENAI_API_KEY=sk-...
   CREDENTIALS_SECRET_KEY=<32 bytes url-safe>
   ```
2. Clique duas vezes no atalho **TranscribeFlow GUI** criado na área de trabalho (ou execute `scripts/run_with_gui.ps1` no PowerShell).
   - O script:
     * Lê as chaves do `.env` ou cai nas variáveis de ambiente.
     * Checa se o Windows é 10+/x64; limpa `runtime_credentials.json` se necessário.
     * Executa `check_install_prereqs.py` (garante segredo/Key válidos).
     * Inicia `TranscribeFlow.exe` no diretório do instalador, abrindo `http://localhost:8000`.
3. Se for necessário rotacionar a chave mais tarde, edite `scripts/install.env` e reexecute o atalho.

### Alternativas (Tree of Thought)
- **Manual**: rodar `Set-Location ...`, exportar `OPENAI_API_KEY`/`CREDENTIALS_SECRET_KEY`, chamar `python scripts/check_install_prereqs.py`, depois `TranscribeFlow.exe`. Esse caminho foi abstraído no PowerShell para evitar erros repetidos.
- **Local engine**: se não quiser a OpenAI, instale `ffmpeg` (ver warning do `pydub`) e defina `ASR_ENGINE=local` antes de disparar o script. O `check_install_prereqs.py` alerta o missing.

### Garantias (CoCoT)
- **Comprovação**: O script valida a chave com `check_install_prereqs.py`, que usa o mesmo runtime credential store testado na suíte.
- **Causalidade**: sem chave url-safe, o `Fernet` falha e impede o boot — por isso o script exige e limpa arquivos antigos.
- **Contexto**: o foco do instalador é Windows 10/11 x64, por isso há checagem explícita da versão.
- **Tendência**: o uso de PowerShell + `check_install_prereqs` e criação de atalho em desktop segue práticas modernas de instalação customizada.

### Mitigações de risco (ReAct)
- Se o script falhar por credencial inválida, ele encerra antes de iniciar o binário e mostra a instrução de correção.
- A criação de atalho só ocorre quando o arquivo ainda não existe ou quando for forçado (`-ForceResetCredentials`), evitando sobreescrever configurações.

### Suite automatizada do instalador

Execute `powershell -ExecutionPolicy Bypass scripts\test_installer_flow.ps1` (de dentro do repositório) após preencher `scripts/install.env`. O script:

- Carrega `OPENAI_API_KEY` e `CREDENTIALS_SECRET_KEY` reais.
- Executa `run_with_gui.ps1` com `-ForceResetCredentials` para gerar um cofre limpo.
- Espera que `TranscribeFlow.exe` inicie e responde em `http://localhost:8000`.
- Mata o processo após a verificação, garantindo build reproducível.

Esse teste cobre _exatamente_ o mesmo código de instalação usado para os usuários finais.

### Visualização de fluxo

```
[install.env / env vars] -> scripts/test_installer_flow.ps1 -> run_with_gui.ps1 -> check_install_prereqs.py -> TranscribeFlow.exe
                                                                         \__________________________/
                                                                                 cria atalho / limpa cofre
```
