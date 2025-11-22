import { jest } from "@jest/globals";

global.requestAnimationFrame = (cb) => cb();

describe("global bindings", () => {
  beforeEach(() => {
    jest.resetModules();
    document.body.innerHTML = `
      <meta name="csrf-token" content="csrf123" />
      <div data-skeleton="panel" hidden aria-hidden="true"></div>
      <div data-surface="panel" aria-busy="false" class=""></div>
      <div data-skeleton="cta" hidden aria-hidden="true"></div>
      <div data-surface="cta" aria-busy="false" class=""></div>
    `;
    window.confirm = jest.fn(() => true);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("prevent submit when confirmation is rejected", async () => {
    window.confirm = jest.fn(() => false);
    document.body.innerHTML += `
      <form data-confirm="Tem certeza?">
        <button type="submit" data-loading="Enviando">Enviar</button>
      </form>
    `;
    const globalMod = await import("../../src/interfaces/web/static/js/global.js");
    globalMod.initGlobal();

    const form = document.querySelector("[data-confirm]");
    const submit = new Event("submit", { cancelable: true });
    form.dispatchEvent(submit);

    expect(window.confirm).toHaveBeenCalled();
    expect(submit.defaultPrevented).toBe(true);
  });

  test("confirmations with acceptance disable button and change label", async () => {
    document.body.innerHTML += `
      <form data-confirm="Prosseguir?">
        <button type="submit" data-loading="Processando...">Enviar</button>
      </form>
    `;
    const globalMod = await import("../../src/interfaces/web/static/js/global.js");
    globalMod.initGlobal();

    const form = document.querySelector("form[data-confirm]");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    const button = form.querySelector("button");
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe("Processando...");
    expect(button.classList.contains("loading")).toBe(true);
  });

  test("surface forms toggle loading state and labels", async () => {
    document.body.innerHTML += `
      <small data-status-updated data-updated-label="status"></small>
      <form data-loading-surface="panel" data-updated-label="status">
        <button type="submit" data-loading="Processando...">Go</button>
      </form>
    `;
    const globalMod = await import("../../src/interfaces/web/static/js/global.js");
    globalMod.initGlobal();

    const form = document.querySelector("form[data-loading-surface]");
    form.dispatchEvent(new Event("submit", { cancelable: true }));

    const skeleton = document.querySelector('[data-skeleton="panel"]');
    const surface = document.querySelector('[data-surface="panel"]');
    expect(skeleton.hidden).toBe(false);
    expect(surface.classList.contains("is-loading")).toBe(true);
    expect(document.querySelector("[data-status-updated]").dataset.state).toBe("loading");
  });

  test("surface forms ignored when enhanced or ajax flagged", async () => {
    document.body.innerHTML += `
      <form data-loading-surface="panel" data-enhanced-process="true">
        <button type="submit">Enviar</button>
      </form>
      <form data-loading-surface="panel" data-ajax="true">
        <button type="submit">Enviar</button>
      </form>
    `;
    const globalMod = await import("../../src/interfaces/web/static/js/global.js");
    globalMod.initGlobal();

    document.querySelectorAll("form").forEach((form) => {
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
    // Should remain untouched
    expect(document.querySelector('[data-skeleton="panel"]').hidden).toBe(true);
    expect(document.querySelector('[data-surface="panel"]').classList.contains("is-loading")).toBe(
      false,
    );
  });

  test("skeleton triggers propagate to loading surface", async () => {
    const globalMod = await import("../../src/interfaces/web/static/js/global.js");
    document.body.innerHTML += `<button data-loading-skeleton="cta"></button>`;
    globalMod.initGlobal();

    document.querySelector("[data-loading-skeleton]").click();
    const skeleton = document.querySelector('[data-skeleton="cta"]');
    expect(skeleton.hidden).toBe(false);
    expect(skeleton.getAttribute("aria-hidden")).toBe("false");
  });

  test("form skeleton trigger uses submit event", async () => {
    const globalMod = await import("../../src/interfaces/web/static/js/global.js");
    document.body.innerHTML += `<form data-loading-skeleton="cta"></form>`;
    globalMod.initGlobal();

    document.querySelector("form[data-loading-skeleton]").dispatchEvent(
      new Event("submit", { cancelable: true }),
    );
    const skeleton = document.querySelector('[data-skeleton="cta"]');
    expect(skeleton.hidden).toBe(false);
  });

  test("flash messages render toasts", async () => {
    document.body.innerHTML += `<div class="flash" data-toast data-toast-variant="success">Tudo certo</div>`;
    const globalMod = await import("../../src/interfaces/web/static/js/global.js");
    globalMod.initGlobal();
    await Promise.resolve();

    const toast = document.querySelector(".toast.toast--success");
    expect(toast).not.toBeNull();
    expect(toast.textContent).toContain("Tudo certo");
  });
});
