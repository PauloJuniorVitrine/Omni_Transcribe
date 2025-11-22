// Checagem estática de tipos do cliente OpenAPI gerado.
import type { paths } from "../../artifacts/openapi";

// Dashboard summary payload deve conter campos esperados usados pelo frontend.
type SummaryResponse =
  paths["/api/dashboard/summary"]["get"]["responses"]["200"]["content"]["application/json"];
const summaryExample: SummaryResponse = {
  summary: { total: 0, awaiting_review: 0, approved: 0, failed: 0 },
  accuracy: { evaluated: 0, needs_review: 0, passing: 0, average_score: null, average_wer: null },
  generated_at: new Date().toISOString(),
};
void summaryExample;

// Logs export retorno JSON lista de eventos.
type LogsExport =
  paths["/api/jobs/{job_id}/logs/export"]["get"]["responses"]["200"]["content"]["application/json"];
const logsExample: LogsExport = [
  { timestamp: new Date().toISOString(), level: "info", event: "pipeline", message: "ok" },
];
void logsExample;
