const { test, expect } = require("@playwright/test");
const fs = require("fs");
const os = require("os");
const path = require("path");

function makeTempAudio(bytes = 4 * 1024 * 1024) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tf-e2e-upload-"));
  const file = path.join(tmp, "long-audio.wav");
  fs.writeFileSync(file, Buffer.alloc(bytes, 1));
  return file;
}

test.describe("upload via GUI handles large payloads", () => {
  test("user uploads ~4MB audio and reaches job detail", async ({ page }) => {
    const audioPath = makeTempAudio();
    await page.goto("/");
    const fileInput = page.locator('input[type="file"][name="file"]');
    await fileInput.setInputFiles(audioPath);
    await page.selectOption('select[name="engine"]', "openai");
    await page.click('button[type="submit"]');
    await page.waitForLoadState("networkidle");

    await expect(page).toHaveURL(/\/jobs\/job-/);
    await expect(page.getByRole("heading", { name: /Job job-/ })).toBeVisible();
    await expect(page.getByText(/Upload recebido/i).first()).toBeVisible();
  });
});
