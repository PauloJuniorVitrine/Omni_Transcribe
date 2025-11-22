import { jest } from "@jest/globals";

jest.setTimeout(15000);

beforeEach(() => {
  document.body.innerHTML = `
    <div
      data-live-summary-endpoint="/api/dashboard/summary"
      data-refresh-interval="0"
      data-loading-surface="summary-cards"
      data-surface="summary-cards"
    >
      <div data-summary-field="total"></div>
      <div data-accuracy-field="average_score"></div>
      <small data-summary-updated></small>
    </div>
  `;
});

afterEach(() => {
  document.body.innerHTML = "";
  jest.clearAllMocks();
});

test("initDashboard updates summary and accuracy fields", async () => {
  const generated = new Date().toISOString();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          summary: { total: 7 },
          accuracy: { average_score: 0.9 },
          generated_at: generated,
        }),
    }),
  );
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(fetch).toHaveBeenCalled();
  expect(document.querySelector('[data-summary-field="total"]').textContent).toBe("7");
  expect(document.querySelector('[data-accuracy-field="average_score"]').textContent).toContain("90.00%");
});

test("initDashboard sets error state when fetch fails", async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();
  const status = document.querySelector("[data-summary-updated]");
  expect(status.dataset.state).toBe("error");
});
