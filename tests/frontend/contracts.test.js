import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const schemaPath = path.resolve(__dirname, "..", "..", "artifacts", "openapi.json");

function loadSchema() {
  if (!fs.existsSync(schemaPath)) {
    throw new Error(`OpenAPI schema não encontrado em ${schemaPath}. Rode "npm run generate:openapi" antes dos testes.`);
  }
  return JSON.parse(fs.readFileSync(schemaPath, "utf-8"));
}

function operation(schema, route, method = "get") {
  return (schema.paths?.[route] || {})[method] || null;
}

function paramNames(operation) {
  return (operation?.parameters || []).map((param) => param.name);
}

describe("Contrato frontend ↔ backend (OpenAPI)", () => {
  const schema = loadSchema();

  test("dashboard summary/incidents expõem 200 e JSON", () => {
    const summary = operation(schema, "/api/dashboard/summary", "get");
    expect(summary).toBeTruthy();
    expect(summary.responses?.["200"]).toBeTruthy();

    const incidents = operation(schema, "/api/dashboard/incidents", "get");
    expect(incidents).toBeTruthy();
    expect(incidents.responses?.["200"]).toBeTruthy();
  });

  test("logs list/export definem parâmetros esperados", () => {
    const logs = operation(schema, "/api/jobs/{job_id}/logs", "get");
    expect(logs).toBeTruthy();
    const names = paramNames(logs);
    expect(names).toEqual(expect.arrayContaining(["job_id"]));

    const exportOp = operation(schema, "/api/jobs/{job_id}/logs/export", "get");
    expect(exportOp).toBeTruthy();
    expect(paramNames(exportOp)).toEqual(expect.arrayContaining(["job_id"]));
  });

  test("process job expõe POST com resposta 200", () => {
    const process = operation(schema, "/api/jobs/{job_id}/process", "post");
    expect(process).toBeTruthy();
    expect(process.responses?.["200"]).toBeTruthy();
  });

  test("templates raw/preview possuem contratos explícitos", () => {
    const raw = operation(schema, "/settings/templates/{template_id}/raw", "get");
    expect(raw).toBeTruthy();
    expect(raw.responses?.["200"]).toBeTruthy();

    const preview = operation(schema, "/settings/templates/preview", "post");
    expect(preview).toBeTruthy();
    expect(preview.requestBody).toBeTruthy();
    expect(preview.responses?.["200"]).toBeTruthy();
  });
});
