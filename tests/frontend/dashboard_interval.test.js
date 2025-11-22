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
});

afterEach(() => {
  document.body.innerHTML = "";
  jest.clearAllMocks();
});

test("initDashboard clears interval on beforeunload", async () => {
  const clearSpy = jest.spyOn(window, "clearInterval");
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  window.dispatchEvent(new Event("beforeunload"));
  expect(clearSpy).toHaveBeenCalled();
});
