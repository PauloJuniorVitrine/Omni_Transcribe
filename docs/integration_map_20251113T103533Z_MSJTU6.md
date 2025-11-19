# Integration Map — EXEC_ID 20251113T103533Z_MSJTU6

| Integration | Layer / Module | Entry Point | Auth / Validation | Status | Risk / Notes |
|-------------|----------------|-------------|-------------------|--------|--------------|
| OpenAI Whisper / GPT-4.x | `src/infrastructure/api/openai_client.py`, `src/application/services/whisper_service.py` | ASR + pós-edição use cases | API key (`OPENAI_API_KEY`), retry/backoff | ✅ Operacional | Monitorar latência/custos |
| OAuth Provider (generic) | `src/interfaces/http/auth_routes.py`, `application/services/session_service.py` | `/auth/login`, `/auth/callback` | Authorization Code + cookie `session_id` | 🟡 Beta | Falta persistir perfis/claims |
| Webhooks externos | `src/interfaces/http/webhook_routes.py`, `application/services/webhook_service.py` | `/webhooks/external` | HMAC SHA-256 + `X-Integration-Id` + timestamp | 🟢 Homolog | Métricas/trace_id expostos |
| GoTranscript Delivery | `src/infrastructure/api/gotranscript_client.py`, `register_delivery.py` | Pós-`RegisterDelivery` | API key (`GOTRANSCRIPT_API_KEY`) | 🟢 Homolog | Registrar SLA real / reprocessamento |
| Storage S3 | `src/infrastructure/api/storage_client.py`, `ZipPackageService` | Backup ZIPs | IAM/MinIO creds (`S3_*`) | 🟢 Homolog | Validar lifecycle/retention |
| Google Sheets / CSV | `CsvSheetService`, `infrastructure/api/sheets_client.py` | Logs e status | Service Account JSON (`GOOGLE_*`) | 🟢 Homolog | Avaliar lotes e quotas |

**Heatmap textual:** `OpenAI (High) > GoTranscript/S3 (Medium-High) > Webhooks (Medium) > OAuth (Medium)`.

**Pendências principais:** instrumentar alertas automáticos para falhas de upload (S3/GoTranscript) e completar autenticação UI.***
