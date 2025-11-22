// Playwright E2E stub using stub_server to simulate end-to-end flow.
const { test, expect } = require("@playwright/test");
const path = require("path");
const { spawn } = require("child_process");

test.describe("dashboard end-to-end (stub server)", () => {
  const baseUrl = "http://127.0.0.1:8001";

  test("user can view dashboard and job detail", async ({ page }) => {
    await page.goto(`${baseUrl}/`);
    await expect(page.getByRole("heading", { name: "TranscribeFlow" })).toBeVisible();
    await page.goto(`${baseUrl}/jobs/job-e2e`);
    await expect(page.getByText("Job job-e2e")).toBeVisible();
  });

  test("user can review and download artifact via stub flows", async ({ page, request }) => {
    const health = await request.get(`${baseUrl}/e2e/health`);
    expect(health.ok()).toBeTruthy();
    const { job_id } = await health.json();
    expect(job_id).toBe("job-e2e");

    await page.goto(`${baseUrl}/jobs/${job_id}`);
    await expect(page.getByRole("heading", { name: /Job job-e2e/i })).toBeVisible();

    const artifact = await request.get(`${baseUrl}/e2e/artifact`);
    expect(artifact.ok()).toBeTruthy();
    const text = await artifact.text();
    expect(text).toContain("Conteudo de teste");

    const review = await request.post(`${baseUrl}/e2e/review`, {
      form: { decision: "approve", notes: "ok" },
    });
    expect(review.ok()).toBeTruthy();
    const reviewPayload = await review.json();
    expect(reviewPayload.status.toLowerCase()).toContain("approved");

    const jobPayload = await (await request.get(`${baseUrl}/e2e/job`)).json();
    expect(jobPayload.status.toLowerCase()).toContain("approved");
  });

  test("user can preview artifact with signed link", async ({ page }) => {
    await page.goto(`${baseUrl}/jobs/job-e2e`);
    const previewButton = page.locator(".artifact-list button", { hasText: "Visualizar" }).first();
    await previewButton.click();
    const modal = page.locator("#artifact-modal");
    await expect(modal).toHaveAttribute("aria-hidden", "false");
    await expect(modal.locator("[data-modal-content]")).toContainText(/Conteudo de teste/i);
  });
});
