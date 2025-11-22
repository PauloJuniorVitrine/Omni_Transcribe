const { test, expect } = require("@playwright/test");

test("upload com auto_process cria job e navega para detalhe", async ({ page }) => {
  await page.goto("/");

  const uploadForm = page.locator('form[action="/jobs/upload"]');
  const fileInput = uploadForm.locator('input[type="file"]');
  await fileInput.setInputFiles({
    name: "sample.wav",
    mimeType: "audio/wav",
    buffer: Buffer.from("fake-audio"),
  });
  await uploadForm.locator('select[name="profile"]').first().selectOption({ index: 0 });
  await uploadForm.locator('select[name="engine"]').first().selectOption("openai");
  await uploadForm.locator('input[name="auto_process"]').check();

  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    uploadForm.locator('button[type="submit"]').click(),
  ]);

  await expect(page).toHaveURL(/\/jobs\/.+/);
  await expect(page.locator(".flash")).toContainText(/process|upload/i);
  await expect(page.locator("h2")).toContainText(/job/i);
});

test("ajuste de flags e credenciais salva com toast", async ({ page }) => {
  // Flags
  await page.goto("/settings/flags");
  const firstFlag = page.locator('input[type="checkbox"][name^="flag_"]').first();
  const initialChecked = await firstFlag.isChecked();
  await firstFlag.setChecked(!initialChecked);
  await Promise.all([
    page.waitForNavigation(),
    page.locator('form[action="/settings/flags"] button[type="submit"]').click(),
  ]);
  await expect(page.locator(".flash, .toast").first()).toContainText(/flags|atualizad/i);

  // Credenciais (Whisper)
  await page.goto("/settings/api");
  const form = page.locator('form[data-updated-target="whisper"]');
  await form.locator('input[name="whisper_api_key"]').fill("sk-playwright");
  await form.locator('select[name="whisper_model"]').selectOption("whisper-1");
  await form.locator('button[type="submit"]').click();
  await expect(page.locator(".toast.toast--success").first()).toContainText(/api|credenciais|whisper/i);
});
