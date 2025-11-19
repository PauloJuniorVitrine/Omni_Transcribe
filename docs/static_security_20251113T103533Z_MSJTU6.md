# Static Security Review – EXEC_ID 20251113T103533Z_MSJTU6

| Item | Localização | Status | Notas/Normas |
| --- | --- | --- | --- |
| Armazenamento de segredos em texto puro | `config/runtime_credentials.py` (antes) | ✅ Mitigado | Agora usa `cryptography.Fernet` + `CREDENTIALS_SECRET_KEY`. Conforme OWASP ASVS 2.1. |
| Dependência de secret obrigatório | `config/runtime_credentials.py` / env | ⚠️ | Falha ao ler payload cifrado se secret não configurado. Documentar e validar em pipeline. |
| Export de artefatos via query string | `/artifacts` (rota) | ✅ | Agora exige token HMAC (`token` + `expires`) quando flag `downloads.signature_required` está ativa, mitigando path tampering. |
| Novos endpoints `/api/jobs/{id}/logs*` | `src/interfaces/http/app.py` | ✅ | Apenas leitura (GET), usa `require_active_session`. Logs sanitizados; avaliar rate-limit futuro. |

## Recomendações
1. Adicionar verificação automática que bloqueie deploy sem `CREDENTIALS_SECRET_KEY` nas pipelines (CI).
2. Para downloads, incluir assinatura temporária ou tokens específicos (PCI-DSS 3.5).
3. Incluir scanner de dependências (pip-audit) e lint de secrets no pipeline, já que `cryptography` foi acrescentado.
