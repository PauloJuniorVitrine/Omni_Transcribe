# Feature Flag Contract Diff – EXEC_ID 20251113T103533Z_MSJTU6

| Flag | Default | Backend Uso | Frontend Uso | Status atual |
| --- | --- | --- | --- | --- |
| `dashboard.live_summary` | true | Dashboard usa resumo dinâmico | Polling JS em `jobs.html` | on |
| `dashboard.live_incidents` | true | Endpoint sempre disponível | Painel visível quando flag on | on |
| `jobs.manual_reprocess` | true | Rota `/jobs/{id}/process` | Formulário AJAX exibido só quando on | on |
| `ui.api_settings` | true | Rota retorna 404 se flag off | Link deve ser ocultado quando off | on |
