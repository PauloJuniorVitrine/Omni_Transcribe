# Feature Flag Map – EXEC_ID 20251113T103533Z_MSJTU6

## Resumo
- O código atual **não implementa** um provedor central de feature flags. As rotas FastAPI (`src/interfaces/http/app.py`) e os módulos JS não fazem condicionamento por flag.
- Configurações que se comportam como toggles (ex.: `settings.google_sheets_enabled`, `settings.s3_enabled`) são carregadas na inicialização, mas não há abstração `FeatureFlag.is_enabled(...)`.

## Impacto
| Módulo | Flag/Toggler | Tipo | Comportamento Atual | Ação Recomendada |
| --- | --- | --- | --- | --- |
| Watcher / Delivery | `GOOGLE_SHEETS_ENABLED`, `S3_ENABLED` | Config boolean | Controlam integrações, porém código acessa direto `settings.*`. | Introduzir wrapper `feature_flags.py` para permitir auditoria/rollout. |
| UI | Nenhum | n/a | Elementos não variam via flag – apenas sessão/flash. | Sem ação imediata. |

## Observações
- Como não há flags, não foi possível gerar `feature_flag_contract_diff` ou `front_visibility_vs_flag`. Para atender o prompt Enterprise+, é necessário criar uma camada de flags e registrar seu estado em arquivos/configs versionados.
