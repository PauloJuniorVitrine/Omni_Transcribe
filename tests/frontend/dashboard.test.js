import { jest } from "@jest/globals";

global.requestAnimationFrame = (cb) => cb();

beforeEach(() => {
  jest.resetModules();
});

afterEach(() => {
  document.body.innerHTML = "";
  jest.clearAllMocks();
});

function buildSummaryDom() {
  document.body.innerHTML = `
    <div
      data-live-summary-endpoint="/api/dashboard/summary"
      data-refresh-interval="0"
      data-loading-surface="summary-cards"
      data-surface="summary-cards"
    >
      <div data-summary-field="total"></div>
      <div data-summary-field="pending"></div>
      <div data-accuracy-field="average_score"></div>
      <div data-accuracy-field="average_wer"></div>
      <small data-summary-updated></small>
      <div data-skeleton="summary-cards" hidden aria-hidden="true"></div>
      <div data-surface="summary-cards" aria-busy="false"></div>
    </div>
  `;
}

function buildIncidentsDom() {
  document.body.innerHTML += `
    <section
      data-live-incidents-endpoint="/api/incidents"
      data-refresh-interval="0"
      data-loading-surface="incidents"
      data-surface="incidents"
      data-empty-label="Nenhum incidente registrado."
    >
      <ul data-incident-list></ul>
      <small data-incidents-updated></small>
      <div data-skeleton="incidents" hidden aria-hidden="true"></div>
      <div data-surface="incidents" aria-busy="false"></div>
    </section>
  `;
}

test("initDashboard updates summary, accuracy and loader state", async () => {
  buildSummaryDom();
  const generated = new Date().toISOString();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          summary: { total: 5, pending: 2 },
          accuracy: { average_score: 0.82, average_wer: 0.1 },
          generated_at: generated,
        }),
    }),
  );
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();
  await Promise.resolve();

  expect(fetch).toHaveBeenCalledWith("/api/dashboard/summary", expect.anything());
  expect(document.querySelector('[data-summary-field="total"]').textContent).toBe("5");
  expect(document.querySelector('[data-summary-field="pending"]').textContent).toBe("2");
  expect(document.querySelector('[data-accuracy-field="average_score"]').textContent).toContain(
    "82.00%",
  );
  expect(document.querySelector('[data-accuracy-field="average_wer"]').textContent).toContain(
    "WER medio 10.00%",
  );
  const status = document.querySelector("[data-summary-updated]");
  expect(status.dataset.state).toBe("success");
  const skeleton = document.querySelector('[data-skeleton="summary-cards"]');
  expect(skeleton.hidden).toBe(true);
  window.dispatchEvent(new Event("beforeunload"));
});

test("initDashboard flags summary error on failed fetch", async () => {
  buildSummaryDom();
  global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();

  expect(document.querySelector("[data-summary-updated]").dataset.state).toBe("error");
  window.dispatchEvent(new Event("beforeunload"));
});

test("initDashboard renders incidents list and clears loader", async () => {
  buildSummaryDom();
  buildIncidentsDom();
  const generated = new Date().toISOString();
  global.fetch = jest.fn((url) => {
    if (url.includes("dashboard/summary")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ summary: { total: 1 }, generated_at: generated }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          items: [
            { event: "Erro", level: "warn", message: "Algo falhou", timestamp_human: "agora", job_id: 9 },
          ],
          generated_at: generated,
        }),
    });
  });
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();

  const item = document.querySelector("[data-incident-list] li");
  expect(item.textContent).toContain("Erro");
  expect(item.querySelector("a").textContent).toContain("Job 9");
  const status = document.querySelector("[data-incidents-updated]");
  expect(status.dataset.state).toBe("success");
  expect(document.querySelector('[data-skeleton="incidents"]').hidden).toBe(true);
  window.dispatchEvent(new Event("beforeunload"));
});

test("initDashboard shows empty incidents placeholder", async () => {
  buildSummaryDom();
  buildIncidentsDom();
  global.fetch = jest.fn((url) => {
    if (url.includes("dashboard/summary")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ summary: { total: 0 } }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          items: [],
          generated_at: null,
        }),
    });
  });
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();
  await Promise.resolve();

  const empty = document.querySelector("[data-incident-list] li");
  expect(empty.textContent).toContain("Nenhum incidente registrado");
  const status = document.querySelector("[data-incidents-updated]");
  expect(status.dataset.state).toBe("success");
  window.dispatchEvent(new Event("beforeunload"));
});

test("initDashboard flags incidents fetch failure", async () => {
  buildSummaryDom();
  buildIncidentsDom();
  global.fetch = jest.fn((url) => {
    if (url.includes("dashboard/summary")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ summary: { total: 0 } }),
      });
    }
    return Promise.resolve({ ok: false });
  });
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();

  const status = document.querySelector("[data-incidents-updated]");
  expect(status.dataset.state).toBe("error");
  window.dispatchEvent(new Event("beforeunload"));
});

test("initDashboard handles missing generated_at and invalid accuracy values", async () => {
  buildSummaryDom();
  const extraField = document.createElement("div");
  extraField.dataset.accuracyField = "custom_metric";
  document.querySelector("[data-live-summary-endpoint]").appendChild(extraField);
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          summary: { total: 2 },
          accuracy: { average_score: Number.NaN, custom_metric: 4 },
        }),
    }),
  );
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();
  await Promise.resolve();

  expect(document.querySelector('[data-accuracy-field="average_score"]').textContent).toBe("-");
  expect(document.querySelector('[data-accuracy-field="custom_metric"]').textContent).toBe("4");
  expect(document.querySelector("[data-summary-updated]").dataset.state).toBe("success");
  window.dispatchEvent(new Event("beforeunload"));
});

test("initDashboard is a no-op without containers", async () => {
  document.body.innerHTML = "";
  global.fetch = jest.fn(() => Promise.reject(new Error("should-not-call")));
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("incidents without job link render basic info", async () => {
  buildIncidentsDom();
  global.fetch = jest.fn((url) => {
    if (url.includes("dashboard/summary")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ summary: { total: 0 } }) });
    }
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          items: [{ event: "Info", level: "info", message: "Mensagem", timestamp_human: "agora" }],
          generated_at: new Date().toISOString(),
        }),
    });
  });
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();
  await Promise.resolve();

  const item = document.querySelector("[data-incident-list] li");
  expect(item.querySelector("a")).toBeNull();
  expect(item.textContent).toContain("Info");
  window.dispatchEvent(new Event("beforeunload"));
});

test("summary handler exits when endpoint missing", async () => {
  document.body.innerHTML = `
    <div data-live-summary-endpoint="">
      <div data-summary-field="total"></div>
    </div>
  `;
  global.fetch = jest.fn();
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("summary update skips when status element is missing", async () => {
  document.body.innerHTML = `
    <div data-live-summary-endpoint="/api/dashboard/summary">
      <div data-summary-field="total"></div>
    </div>
  `;
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ summary: { total: 1 } }),
    }),
  );
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  await Promise.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(document.querySelector('[data-summary-field="total"]').textContent).toBe("1");
});

test("incidents handler exits when endpoint missing or status unavailable", async () => {
  document.body.innerHTML = `
    <section data-live-incidents-endpoint="">
      <ul data-incident-list></ul>
    </section>
  `;
  global.fetch = jest.fn();
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("initDashboard clears interval on beforeunload", async () => {
  buildSummaryDom();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ summary: { total: 1 } }),
    }),
  );
  const clearSpy = jest.spyOn(window, "clearInterval");
  const dashboard = await import("../../src/interfaces/web/static/js/dashboard.js");
  dashboard.initDashboard();
  window.dispatchEvent(new Event("beforeunload"));
  expect(clearSpy).toHaveBeenCalled();
});
