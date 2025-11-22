import { jest } from "@jest/globals";

jest.setTimeout(15000);

global.requestAnimationFrame = (cb) => cb();

beforeAll(() => {
  // jsdom lacks dialog methods
  HTMLDialogElement.prototype.showModal = jest.fn();
  HTMLDialogElement.prototype.close = jest.fn();
});

describe("settings ajax flows", () => {
  beforeEach(() => {
    jest.resetModules();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("initSettings handles ajax success and updates label", async () => {
    document.body.innerHTML = `
      <meta name="csrf-token" content="csrf123" />
      <div data-skeleton="prefs" hidden aria-hidden="true"></div>
      <div data-surface="prefs" aria-busy="false" class=""></div>
      <span data-updated-label="profile"></span>
      <form data-ajax="true" data-loading-surface="prefs" data-updated-target="profile" action="/settings/save">
        <input name="field" value="abc" />
        <button type="submit" data-loading="Processando...">Salvar</button>
      </form>
    `;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ message: "ok", updated_at_human: "10:00" }),
      }),
    );
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initSettings();

    const form = document.querySelector('form[data-ajax="true"]');
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await Promise.resolve();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(document.querySelector('[data-updated-label="profile"]').textContent).toContain("10:00");
    const surface = document.querySelector('[data-surface="prefs"]');
    expect(surface.classList.contains("is-loading")).toBe(false);
  });

  test("initSettings shows error toast when ajax fails", async () => {
    document.body.innerHTML = `
      <meta name="csrf-token" content="csrf123" />
      <form data-ajax="true" data-loading-surface="prefs" action="/settings/save">
        <button type="submit">Salvar</button>
      </form>
      <div data-skeleton="prefs" hidden aria-hidden="true"></div>
      <div data-surface="prefs" aria-busy="false" class=""></div>
    `;
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initSettings();

    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await Promise.resolve();
    await Promise.resolve();

    const toast = document.querySelector(".toast.toast--error");
    expect(toast).not.toBeNull();
  });

  test("ajax failure restores submit button text", async () => {
    document.body.innerHTML = `
      <meta name="csrf-token" content="csrf123" />
      <form data-ajax="true" data-loading-surface="prefs" action="/settings/save">
        <button type="submit" data-loading="Processando...">Salvar</button>
      </form>
      <div data-skeleton="prefs" hidden aria-hidden="true"></div>
      <div data-surface="prefs" aria-busy="false" class=""></div>
    `;
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initSettings();

    const button = document.querySelector("button[type='submit']");
    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await Promise.resolve();
    expect(button.disabled).toBe(false);
    expect(button.textContent).toBe("Salvar");
  });

  test("ajax submit ignored when event already prevented", async () => {
    document.body.innerHTML = `
      <meta name="csrf-token" content="csrf123" />
      <form data-ajax="true" data-loading-surface="prefs" action="/settings/save">
        <button type="submit">Salvar</button>
      </form>
      <div data-skeleton="prefs" hidden aria-hidden="true"></div>
      <div data-surface="prefs" aria-busy="false" class=""></div>
    `;
    global.fetch = jest.fn();
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initSettings();

    const event = new Event("submit", { cancelable: true });
    event.preventDefault();
    document.querySelector("form").dispatchEvent(event);
    await Promise.resolve();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe("template settings interactions", () => {
  beforeEach(() => {
    jest.resetModules();
    window.confirm = jest.fn(() => true);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  function buildTemplateDom() {
    document.body.innerHTML = `
      <meta name="csrf-token" content="csrf123" />
      <dialog id="template-edit-modal">
        <form data-template-edit-form>
          <input name="template_id" />
          <input name="name" />
          <input name="description" />
          <input name="locale" />
          <textarea name="body"></textarea>
        </form>
        <button data-dismiss-modal></button>
      </dialog>
      <form action="/settings/templates">
        <textarea name="body"></textarea>
      </form>
      <button
        data-template-edit="tpl-1"
        data-template-name="Custom"
        data-template-description="Desc"
        data-template-locale="pt-BR"
      ></button>
      <button data-template-delete="tpl-1"></button>
      <button data-template-preview="create"></button>
      <div data-template-preview-output="create"></div>
      <button data-template-preview="edit"></button>
      <div data-template-preview-output="edit"></div>
      <div data-template-row="tpl-1"></div>
    `;
  }

  test("edit, preview and delete template flows", async () => {
    buildTemplateDom();
    global.fetch = jest.fn((url, options = {}) => {
      if (url.endsWith("/raw")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              name: "FromAPI",
              description: "Body",
              locale: "en",
              body: "Hello",
            }),
        });
      }
      if (url.includes("/preview")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ rendered: "Preview text" }),
        });
      }
      if (url.endsWith("/tpl-1") && options.method === "DELETE") {
        return Promise.resolve({ ok: true });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });

    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initTemplateSettings();

    document.querySelector('[data-template-edit="tpl-1"]').click();
    await Promise.resolve();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));

    const bodyField = document.querySelector('textarea[name="body"]');
    expect(bodyField.value).toBe("Hello");
    expect(document.getElementById("template-edit-modal").showModal).toHaveBeenCalled();

    // preview using create form
    const createFormBody = document.querySelector('form[action="/settings/templates"] textarea[name="body"]');
    createFormBody.value = "Example body";
    document.querySelector('[data-template-preview="create"]').click();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(global.fetch).toHaveBeenCalledWith(
      "/settings/templates/preview",
      expect.objectContaining({ method: "POST" }),
    );
    expect(document.querySelector('[data-template-preview-output="create"]').textContent).toBe(
      "Preview text",
    );

    // delete template
    document.querySelector('[data-template-delete="tpl-1"]').click();
    await Promise.resolve();
    expect(document.querySelector('[data-template-row="tpl-1"]')).toBeNull();
    expect(document.querySelector(".toast.toast--success")).not.toBeNull();
  });

  test("preview warns when body is empty", async () => {
    buildTemplateDom();
    global.fetch = jest.fn();
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initTemplateSettings();

    document.querySelector('[data-template-preview="create"]').click();
    await Promise.resolve();

    expect(document.querySelector(".toast.toast--warning")).not.toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("edit preview uses dialog form and fetch failure shows error", async () => {
    buildTemplateDom();
    global.fetch = jest.fn((url) => {
      if (url.endsWith("/raw")) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) });
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve(null) });
    });
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initTemplateSettings();
    document.querySelector('[data-template-edit="tpl-1"]').click();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector(".toast.toast--error")).not.toBeNull();
  });

  test("template delete respects user cancellation", async () => {
    buildTemplateDom();
    window.confirm = jest.fn(() => false);
    const fetchSpy = jest.fn();
    global.fetch = fetchSpy;
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initTemplateSettings();
    document.querySelector('[data-template-delete="tpl-1"]').click();
    await Promise.resolve();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(document.querySelector('[data-template-row="tpl-1"]')).not.toBeNull();
  });

  test("template delete surfaces backend errors", async () => {
    buildTemplateDom();
    global.fetch = jest.fn((url, options = {}) => {
      if (url.endsWith("/raw")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ body: "body", locale: "pt", name: "n", description: "d" }),
        });
      }
      if (options.method === "DELETE") {
        return Promise.resolve({ ok: false });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initTemplateSettings();
    document.querySelector('[data-template-edit="tpl-1"]').click();
    await Promise.resolve();
    document.querySelector('[data-template-delete="tpl-1"]').click();
    await Promise.resolve();
    expect(document.querySelector('[data-template-row="tpl-1"]')).not.toBeNull();
    expect(document.querySelector(".toast.toast--error")).not.toBeNull();
  });

  test("template update handles failure without reload", async () => {
    buildTemplateDom();
    global.fetch = jest.fn((url, options = {}) => {
      if (url.endsWith("/raw")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ body: "content", locale: "pt", name: "Name", description: "Desc" }),
        });
      }
      if (url.includes("/update")) {
        return Promise.resolve({ ok: false });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ rendered: "Praevia" }) });
    });
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initTemplateSettings();

    document.querySelector('[data-template-edit="tpl-1"]').click();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
    document.querySelector('input[name="template_id"]').value = "tpl-1";
    const form = document.querySelector("[data-template-edit-form]");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(document.querySelector(".toast.toast--error")).not.toBeNull();
  });

  test("edit preview renders output for edit mode", async () => {
    buildTemplateDom();
    global.fetch = jest.fn((url) => {
      if (url.endsWith("/raw")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ body: "template body", locale: "pt", name: "Nome", description: "Desc" }),
        });
      }
      if (url.includes("/preview")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ rendered: "Rendered edit" }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initTemplateSettings();
    document.querySelector('[data-template-edit="tpl-1"]').click();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
    document.querySelector('textarea[name="body"]').value = "Valor";
    document.querySelector('[data-template-preview="edit"]').click();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector('[data-template-preview-output="edit"]').textContent).toBe("Rendered edit");
  });

  test("initTemplateSettings returns when modal is missing", async () => {
    document.body.innerHTML = "<div></div>";
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    expect(() => settings.initTemplateSettings()).not.toThrow();
  });
});

describe("settings ajax flows - edge cases", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("uses custom error message on ajax failure", async () => {
    document.body.innerHTML = `
      <meta name="csrf-token" content="csrf123" />
      <form data-ajax="true" data-loading-surface="prefs" data-error-message="Falhou" action="/settings/save">
        <button type="submit">Salvar</button>
      </form>
      <div data-skeleton="prefs" hidden aria-hidden="true"></div>
      <div data-surface="prefs" aria-busy="false" class=""></div>
    `;
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
    const settings = await import("../../src/interfaces/web/static/js/settings.js");
    settings.initSettings();

    document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await Promise.resolve();
    expect(document.querySelector(".toast.toast--error").textContent).toContain("Falhou");
  });
});
