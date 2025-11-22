const { test, expect } = require("@playwright/test");

test("fluxo completo: dashboard -> detalhe -> logs/artefatos -> atualização de template", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('[data-summary-field="total"]')).toBeVisible();

  // Navega para o job gerado pelo stub e valida cabeçalho.
  await page.getByText("Ver detalhes").first().click();
  await expect(page).toHaveURL(/\/jobs\/.+/);
  await expect(page.locator("h2")).toContainText("job");

  // Processa job via ação AJAX.
  const processForm = page.locator('[data-enhanced-process]');
  if (await processForm.count()) {
    await processForm.locator('button[type="submit"]').click();
    await expect(page.locator("[data-process-status]")).toBeVisible({ timeout: 15000 });
  }

  // Abre pré-visualização de artefato (exercita /artifacts com token).
  const previewButton = page.locator("[data-preview-url]").first();
  await previewButton.click();
  const modal = page.locator("#artifact-modal");
  await expect(modal).toHaveClass(/open/);
  await expect(modal.locator("[data-modal-content]")).toContainText(/Conteudo|Transcri|Arquivo|Sem conteudo/i);
  await modal.locator("[data-dismiss-modal]").first().click({ force: true });
  await page.keyboard.press("Escape");
  await expect(modal).toBeHidden({ timeout: 5000 });

  // Atualiza template de entrega e idioma (POST nos endpoints de contrato).
  await page.locator("[data-template-selector]").selectOption({ index: 0 });
  await page.locator('[data-template-form="true"] button[type="submit"]').click();
  await expect(page.locator("[data-template-updated]")).toContainText(/Atualizado/i);

  const localeForm = page.locator('form[action*="/locale"]');
  if (await localeForm.count()) {
    await localeForm.locator("select[name='delivery_locale']").selectOption({ index: 0 });
    await localeForm.locator('button[type="submit"]').click();
    await expect(page.locator('[data-updated-label="locale"]')).toContainText(/Atualizado|Idioma/i);
  }

  // Filtra logs (chama /api/jobs/{id}/logs) e garante renderização.
  await page.locator('[data-log-filter="level"]').selectOption("");
  await page.locator('[data-log-form]').dispatchEvent("submit");
  await expect(page.locator("[data-log-list] li").first()).toBeVisible();
});
