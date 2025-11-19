# Directory Violations – EXEC_ID 20251113T103533Z_MSJTU6

## Regras
- Camada `domain/` deve conter apenas entidades e value objects.
- `application/` abriga use cases e services.
- `infrastructure/` armazena adaptadores/repositórios concretos.
- `interfaces/` expõe HTTP/UI.

## Achados
| ID | Arquivo | Violação | Sugestão |
| --- | --- | --- | --- |
| DIRFIX-001 | `src/interfaces/http/app.py` | Controller mistura lógica de domínio (leitura de artefatos em disco) e interface. | Extrair `JobDetailPresenter` em `application/` ou `infrastructure/services` e consumir via controller. |
| DIRFIX-002 | `application/logging_config.py` | Configuração técnica dentro de `application/` (deveria residir em infraestrutura). | Mover para `infrastructure/logging` e reaproveitar nos entrypoints. |
| DIRFIX-003 | `src/interfaces/web/static/js/core.js` | OK – fica em interfaces. (Nenhuma ação). | – |

## Observações
- A maioria dos módulos segue a estrutura Clean/Hexagonal, mas controllers HTTP ainda fazem IO direto.  
- Ação recomendada: criar diretório `application/presenters` ou `infrastructure/services/web` para centralizar transformações/paginação.
