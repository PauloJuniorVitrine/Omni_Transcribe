const { test, expect } = require("@playwright/test");

test("dashboard shows summary cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('[data-summary-field="total"]')).toHaveText("1");
  await expect(page.locator(".summary-card").first()).toBeVisible();
  await expect(page.locator(".session-meta strong")).toContainText("Sessao");
});

test("job detail loads and shows artifacts", async ({ page }) => {
  await page.goto("/");
  await page.click("text=Ver detalhes");
  await expect(page.locator("h2")).toContainText("job-e2e");
  await expect(page.locator(".artifact-list li").first()).toBeVisible();
});

test("filters reflect query params and show empty state for mismatched status", async ({ page }) => {
  await page.goto("/?status=approved");
  await expect(page.locator('select[name="status"]')).toHaveValue("approved");
  await expect(page.locator("tbody td").first()).toHaveText("Nenhum job encontrado.");
});

test("API settings form saves whisper credentials via AJAX", async ({ page }) => {
  await page.goto("/settings/api");
  const whisperForm = page.locator('form[data-updated-target="whisper"]');
  await whisperForm.locator('input[name="whisper_api_key"]').fill("sk-test-123");
  await whisperForm.locator('select[name="whisper_model"]').selectOption("whisper-1");
  await whisperForm.locator('button[type="submit"]').click();

  const toast = page.locator(".toast.toast--success");
  await expect(toast).toContainText("Whisper");
  await expect(page.locator('[data-updated-label="whisper"]')).toContainText("Atualizado");
});

test("job detail allows selecting delivery template", async ({ page }) => {
  await page.goto("/jobs/job-e2e");
  await page.locator('[data-template-selector]').selectOption("briefing");
  await page.locator('[data-template-form="true"] button[type="submit"]').click();
  await expect(page.locator("[data-template-updated]")).toContainText("Atualizado");
});

test("template settings allow creating new template entries", async ({ page }) => {
  await page.goto("/settings/templates");
  const slug = `pw-${Date.now()}`;
  const createForm = page.locator('form[action="/settings/templates"]');
  await createForm.locator('input[name="template_id"]').fill(slug);
  await createForm.locator('input[name="name"]').fill("Playwright Template");
  await createForm.locator('input[name="locale"]').fill("en-US");
  await createForm.locator('textarea[name="body"]').fill("{{header}}\n\nTest template for {{transcript}}");
  await createForm.locator('[data-template-preview="create"]').click();
  await expect(page.locator('[data-template-preview-output="create"]')).toContainText("Arquivo original");
  await createForm.locator('button[type="submit"]').click();
  await expect(page.locator(".toast.toast--success").last()).toContainText("Template");
  await page.reload();
  await expect(page.locator(".template-table")).toContainText(slug);
  page.once("dialog", (dialog) => dialog.accept());
  await page.locator(`[data-template-row="${slug}"] [data-template-delete="${slug}"]`).click();
  await expect(page.locator(".toast.toast--success").last()).toContainText("removido", { ignoreCase: true });
});
