import { jest } from "@jest/globals";

beforeEach(() => {
  document.body.innerHTML = `
    <div
      data-live-summary-endpoint="/api/dashboard/summary"
      data-refresh-interval="0"
      data-loading-surface="summary-cards"
      data-surface="summary-cards"
    >
      <div data-summary-field="total"></div>
      <small data-summary-updated></small>
    </div>
  `;
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ summary: { total: 5 }, generated_at: new Date().toISOString() }),
    }),
  );
});

afterEach(() => {
  document.body.innerHTML = "";
  jest.clearAllMocks();
});

test("initDashboard updates summary via fetch", async () => {
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  // wait a tick
  await Promise.resolve();
  expect(fetch).toHaveBeenCalled();
});
