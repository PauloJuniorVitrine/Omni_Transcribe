import { jest } from "@jest/globals";

global.requestAnimationFrame = (cb) => cb();

describe("core helpers", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <meta name="csrf-token" content="abc123" />
      <div data-skeleton="area" hidden aria-hidden="true"></div>
      <div data-surface="area" aria-busy="false" class=""></div>
    `;
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  test("withCsrf and appendCsrf inject token", async () => {
    const core = await import("../../src/interfaces/web/static/js/core.js");
    const headers = core.withCsrf();
    expect(headers["X-CSRF-Token"]).toBe("abc123");

    const fd = new FormData();
    core.appendCsrf(fd);
    expect(fd.get("csrf_token")).toBe("abc123");
  });

  test("setSurfaceLoading toggles skeleton and aria flags", async () => {
    const core = await import("../../src/interfaces/web/static/js/core.js");
    core.setSurfaceLoading("area", true);

    const skeleton = document.querySelector('[data-skeleton="area"]');
    const surface = document.querySelector('[data-surface="area"]');
    expect(skeleton.hidden).toBe(false);
    expect(skeleton.getAttribute("aria-hidden")).toBe("false");
    expect(surface.classList.contains("is-loading")).toBe(true);
    expect(surface.getAttribute("aria-busy")).toBe("true");

    core.setSurfaceLoading("area", false);
    expect(skeleton.hidden).toBe(true);
    expect(surface.classList.contains("is-loading")).toBe(false);
  });

  test("getCsrfToken caches value and respects meta changes after reset", async () => {
    const core = await import("../../src/interfaces/web/static/js/core.js");
    expect(core.getCsrfToken()).toBe("abc123");
    document.querySelector('meta[name="csrf-token"]').setAttribute("content", "changed");
    expect(core.getCsrfToken()).toBe("abc123");
    jest.resetModules();
    const fresh = await import("../../src/interfaces/web/static/js/core.js");
    expect(fresh.getCsrfToken()).toBe("changed");
  });

  test("appendCsrf does not overwrite existing tokens", async () => {
    const core = await import("../../src/interfaces/web/static/js/core.js");
    const fd = new FormData();
    fd.append("csrf_token", "existing");
    core.appendCsrf(fd);
    expect(fd.get("csrf_token")).toBe("existing");
  });

  test("withCsrf can return headers unchanged when token missing", async () => {
    document.querySelector('meta[name="csrf-token"]').remove();
    jest.resetModules();
    const core = await import("../../src/interfaces/web/static/js/core.js");
    const headers = core.withCsrf({ Accept: "application/json" });
    expect(headers["X-CSRF-Token"]).toBeUndefined();
  });

  test("updateLabelState clears dataset when no state provided", async () => {
    const core = await import("../../src/interfaces/web/static/js/core.js");
    const label = document.createElement("span");
    label.dataset.state = "old";
    document.body.appendChild(label);
    core.updateLabelState("span", "Novo");
    expect(label.textContent).toBe("Novo");
    expect(label.dataset.state).toBeUndefined();
  });

  test("showToast renders and schedules removal", async () => {
    jest.useFakeTimers();
    const core = await import("../../src/interfaces/web/static/js/core.js");
    core.showToast("teste", "info", { title: "Aviso" });
    expect(document.querySelector(".toast.toast--info")).not.toBeNull();
    jest.runOnlyPendingTimers();
    jest.runOnlyPendingTimers();
    expect(document.querySelector(".toast.toast--info")).toBeNull();
    jest.useRealTimers();
  });
});
