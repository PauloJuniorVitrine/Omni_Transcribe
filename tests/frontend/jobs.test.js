import { jest } from "@jest/globals";

jest.setTimeout(15000);

global.requestAnimationFrame = (cb) => cb();

function setupModalDom() {
  document.body.innerHTML = `
    <div id="artifact-modal" aria-hidden="true">
      <div class="modal-dialog" tabindex="-1"></div>
      <div data-modal-content></div>
      <div data-modal-title></div>
      <button data-dismiss-modal>Close</button>
    </div>
    <button
      data-preview-url="/artifacts/file.txt"
      data-preview-extension="txt"
      data-preview-label="TXT"
      data-dismiss-modal
    ></button>
  `;
  const dialog = document.querySelector(".modal-dialog");
  dialog.focus = jest.fn();
}

test("preview opens modal and loads content", async () => {
  setupModalDom();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      text: () => Promise.resolve("conteudo"),
    }),
  );
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();

  const button = document.querySelector("[data-preview-url]");
  button.click();
  await new Promise((resolve) => setTimeout(resolve, 0));

  const modal = document.getElementById("artifact-modal");
  expect(modal.classList.contains("open")).toBe(true);
  expect(document.querySelector("[data-modal-content]").textContent).toContain("conteudo");
});

test("preview closes on escape and ignores buttons without url", async () => {
  setupModalDom();
  const trigger = document.querySelector("[data-preview-url]");
  trigger.focus = jest.fn();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      text: () => Promise.resolve("conteudo"),
    }),
  );
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  trigger.focus();
  trigger.click();
  await Promise.resolve();

  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
  expect(document.getElementById("artifact-modal").classList.contains("open")).toBe(false);
  expect(trigger.focus).toHaveBeenCalled();

  const noUrl = document.createElement("button");
  noUrl.dataset.previewExtension = "txt";
  document.body.appendChild(noUrl);
  noUrl.click();
  expect(global.fetch).toHaveBeenCalledTimes(1);
});

test("preview modal closes on overlay and dismiss button", async () => {
  setupModalDom();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      text: () => Promise.resolve("conteudo"),
    }),
  );
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  const trigger = document.querySelector("[data-preview-url]");
  trigger.click();
  await Promise.resolve();

  const modal = document.getElementById("artifact-modal");
  modal.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  expect(modal.classList.contains("open")).toBe(false);

  trigger.click();
  await Promise.resolve();
  modal.querySelector("[data-dismiss-modal]").dispatchEvent(new MouseEvent("click", { bubbles: true }));
  expect(modal.classList.contains("open")).toBe(false);
});

test("preview warns when extension unsupported and handles fetch error", async () => {
  setupModalDom();
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();

  const button = document.querySelector("[data-preview-url]");
  button.dataset.previewExtension = "pdf";
  button.click();
  expect(document.querySelector(".toast.toast--warning")).not.toBeNull();

  // set supported extension but failing fetch
  button.dataset.previewExtension = "txt";
  global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
  button.click();
  await Promise.resolve();
  expect(document.querySelector(".toast.toast--error")).not.toBeNull();

  // empty content fallback
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      text: () => Promise.resolve(""),
    }),
  );
  button.click();
  await Promise.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(document.querySelector("[data-modal-content]").textContent).toContain("Sem");
});

test("job logs are fetched and rendered", async () => {
  document.body.innerHTML = `
    <section
      data-job-logs-endpoint="/api/logs"
      data-job-logs-export="/api/logs/export"
      data-surface="logs-timeline"
    >
      <div data-log-list></div>
      <form data-log-form>
        <select data-log-filter="level"><option value=""></option></select>
        <input data-log-filter="event" />
        <button type="submit">Filtrar</button>
        <button type="button" data-log-reset>Limpar</button>
      </form>
      <div data-log-controls hidden>
        <button type="button" data-log-more hidden>Mais</button>
        <button type="button" data-log-export="json"></button>
      </div>
      <small data-logs-updated></small>
    </section>
  `;
  const generated = new Date().toISOString();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          logs: [{ event: "evt", level: "info", message: "msg", timestamp: generated }],
          has_more: false,
          page: 1,
          generated_at: generated,
        }),
    }),
  );
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  await new Promise((resolve) => setTimeout(resolve, 0));

  expect(fetch).toHaveBeenCalled();
  const list = document.querySelector("[data-log-list]");
  expect(list.textContent).toContain("evt");
  const status = document.querySelector("[data-logs-updated]");
  expect(status.dataset.state).toBe("success");
});

test("job logs render empty state", async () => {
  document.body.innerHTML = `
    <section
      data-job-logs-endpoint="/api/logs"
      data-job-logs-export="/api/logs/export"
      data-surface="logs-timeline"
    >
      <div data-log-list></div>
      <form data-log-form>
        <select data-log-filter="level"><option value=""></option></select>
        <input data-log-filter="event" />
        <button type="submit">Filtrar</button>
        <button type="button" data-log-reset>Limpar</button>
      </form>
      <div data-log-controls hidden>
        <button type="button" data-log-more hidden>Mais</button>
        <button type="button" data-log-export="json"></button>
      </div>
      <small data-logs-updated></small>
    </section>
  `;
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ logs: [], has_more: false, page: 1 }),
    }),
  );
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  await Promise.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(document.querySelector("[data-log-list]").textContent).toContain("Nenhum evento registrado.");
});

test("job logs handle pagination and errors", async () => {
  document.body.innerHTML = `
    <section
      data-job-logs-endpoint="/api/logs"
      data-job-logs-export="/api/logs/export"
      data-surface="logs-timeline"
    >
      <div data-log-list></div>
      <form data-log-form>
        <select data-log-filter="level"><option value=""></option></select>
        <input data-log-filter="event" />
        <button type="submit">Filtrar</button>
        <button type="button" data-log-reset>Limpar</button>
      </form>
      <div data-log-controls hidden>
        <button type="button" data-log-more hidden>Mais</button>
        <button type="button" data-log-export="json"></button>
      </div>
      <small data-logs-updated></small>
    </section>
  `;
  const generated = new Date().toISOString();
  const successResponse = {
    ok: true,
    json: () =>
      Promise.resolve({
        logs: [{ event: "evt2", level: "warn", message: "msg", timestamp: generated }],
        has_more: true,
        page: 1,
        generated_at: generated,
      }),
  };
  const secondPage = {
    ok: true,
    json: () =>
      Promise.resolve({
        logs: [{ event: "evt3", level: "info", message: "next", timestamp: generated }],
        has_more: false,
        page: 2,
        generated_at: generated,
      }),
  };
  let call = 0;
  global.fetch = jest.fn(() => {
    call += 1;
    if (call === 1) return Promise.resolve(successResponse);
    if (call === 2) return Promise.resolve(secondPage);
    return Promise.resolve({ ok: false });
  });
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  await new Promise((resolve) => setTimeout(resolve, 0));

  document.querySelector("[data-log-more]").click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(document.querySelector("[data-log-list]").textContent).toContain("evt3");
});

test("job logs set error state when fetch fails", async () => {
  document.body.innerHTML = `
    <section
      data-job-logs-endpoint="/api/logs"
      data-job-logs-export="/api/logs/export"
      data-surface="logs-timeline"
    >
      <div data-log-list></div>
      <form data-log-form>
        <select data-log-filter="level"><option value=""></option></select>
        <input data-log-filter="event" />
        <button type="submit">Filtrar</button>
        <button type="button" data-log-reset>Limpar</button>
      </form>
      <div data-log-controls hidden>
        <button type="button" data-log-more hidden>Mais</button>
        <button type="button" data-log-export="json"></button>
      </div>
      <small data-logs-updated></small>
    </section>
  `;
  global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  await Promise.resolve();
  expect(document.querySelector("[data-logs-updated]").dataset.state).toBe("error");
});

test("job logs skip when endpoint missing", async () => {
  document.body.innerHTML = `
    <section data-surface="logs-timeline">
      <div data-log-list></div>
    </section>
  `;
  global.fetch = jest.fn();
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  await Promise.resolve();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("process action aborts when event already prevented", async () => {
  document.body.innerHTML = `
    <section>
      <div data-process-status></div>
      <form data-enhanced-process="true" data-process-endpoint="/api/jobs/1/process" data-loading-surface="job-actions">
        <button type="submit">Processar</button>
      </form>
      <div data-skeleton="job-actions" hidden></div>
      <div data-surface="job-actions"></div>
    </section>
  `;
  const fetchSpy = jest.fn();
  global.fetch = fetchSpy;
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  const event = new Event("submit", { cancelable: true });
  event.preventDefault();
  document.querySelector("[data-enhanced-process]").dispatchEvent(event);
  expect(fetchSpy).not.toHaveBeenCalled();
});

test("process action uses custom labels and restores button text", async () => {
  document.body.innerHTML = `
    <div data-process-status></div>
    <form data-enhanced-process="true" data-process-endpoint="/api/jobs/1/process" data-loading-surface="job-actions" data-process-success-label="Tudo certo">
      <button type="submit">Processar</button>
    </form>
    <div data-skeleton="job-actions" hidden></div>
    <div data-surface="job-actions"></div>
  `;
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: "processing" }),
    }),
  );
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  const form = document.querySelector("[data-enhanced-process]");
  const button = form.querySelector("button");
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));
  const status = document.querySelector("[data-process-status]");
  expect(status.textContent).toContain("Tudo certo");
  expect(button.disabled).toBe(false);
  expect(button.textContent).toBe("Processar");
});

test("process action updates status on success", async () => {
  document.body.innerHTML = `
    <section>
      <div data-process-status></div>
      <form data-enhanced-process="true" data-process-endpoint="/api/jobs/1/process" data-loading-surface="job-actions">
        <button type="submit">Processar</button>
      </form>
      <div data-skeleton="job-actions" hidden></div>
      <div data-surface="job-actions"></div>
    </section>
  `;
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: "processing" }),
    }),
  );
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();

  const form = document.querySelector("[data-enhanced-process]");
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));
  const status = document.querySelector("[data-process-status]");
  expect(status.dataset.state).toBe("success");
});

test("process action sets error state when fetch fails", async () => {
  document.body.innerHTML = `
    <section>
      <div data-process-status></div>
      <form data-enhanced-process="true" data-process-endpoint="/api/jobs/1/process" data-loading-surface="job-actions">
        <button type="submit">Processar</button>
      </form>
      <div data-skeleton="job-actions" hidden></div>
      <div data-surface="job-actions"></div>
    </section>
  `;
  global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();

  const form = document.querySelector("[data-enhanced-process]");
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await Promise.resolve();
  const status = document.querySelector("[data-process-status]");
  expect(status.dataset.state).toBe("error");
});

test("template selector updates descriptions", async () => {
  document.body.innerHTML = `
    <select data-template-selector>
      <option value="1" data-description="Primeiro">Opt1</option>
      <option value="2" data-description="Segundo" selected>Opt2</option>
    </select>
    <div data-template-description></div>
  `;
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  expect(document.querySelector("[data-template-description]").textContent).toBe("Segundo");
  const select = document.querySelector("[data-template-selector]");
  select.value = "1";
  select.dispatchEvent(new Event("change"));
  expect(document.querySelector("[data-template-description]").textContent).toBe("Primeiro");
});

test("exports include active filters", async () => {
  document.body.innerHTML = `
    <section
      data-job-logs-endpoint="/api/logs"
      data-job-logs-export="/api/logs/export"
      data-surface="logs-timeline"
    >
      <div data-log-list></div>
      <form data-log-form>
        <select data-log-filter="level">
          <option value=""></option>
          <option value="warn" selected>Warn</option>
        </select>
        <input data-log-filter="event" value="evt" />
        <button type="submit">Filtrar</button>
        <button type="button" data-log-reset>Limpar</button>
      </form>
      <div data-log-controls hidden>
        <button type="button" data-log-more hidden>Mais</button>
        <button type="button" data-log-export="json"></button>
      </div>
      <small data-logs-updated></small>
    </section>
  `;
  const generated = new Date().toISOString();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          logs: [],
          has_more: false,
          page: 1,
          generated_at: generated,
        }),
    }),
  );
  const openSpy = jest.spyOn(window, "open").mockImplementation(() => null);
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  await Promise.resolve();
  document.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  await Promise.resolve();
  document.querySelector("[data-log-export]").click();
  expect(openSpy).toHaveBeenCalledWith(
    expect.stringContaining("level=warn&event=evt"),
    "_blank",
  );
});

test("initJobDetail is safe when markup is missing", async () => {
  document.body.innerHTML = "<div></div>";
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  expect(true).toBe(true);
});

test("log export opens window with params", async () => {
  document.body.innerHTML = `
    <section
      data-job-logs-endpoint="/api/logs"
      data-job-logs-export="/api/logs/export"
      data-surface="logs-timeline"
    >
      <div data-log-list></div>
      <form data-log-form>
        <select data-log-filter="level"><option value=""></option></select>
        <input data-log-filter="event" />
        <button type="submit">Filtrar</button>
        <button type="button" data-log-reset>Limpar</button>
      </form>
      <div data-log-controls hidden>
        <button type="button" data-log-more hidden>Mais</button>
        <button type="button" data-log-export="json" data-log-export>Exportar</button>
      </div>
      <small data-logs-updated></small>
    </section>
  `;
  const generated = new Date().toISOString();
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          logs: [],
          has_more: false,
          page: 1,
          generated_at: generated,
        }),
    }),
  );
  const openSpy = jest.spyOn(window, "open").mockImplementation(() => null);
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  jobs.initJobDetail();
  await Promise.resolve();

  document.querySelector("[data-log-export]").click();
  expect(openSpy).toHaveBeenCalled();
});
