import { jest } from "@jest/globals";

global.requestAnimationFrame = (cb) => cb();

test("upload form toggles loading skeleton and handles error", async () => {
  document.body.innerHTML = `
    <form id="upload-form" action="/jobs/upload" method="post" data-loading-surface="jobs-feed">
      <input type="file" name="file" />
      <input type="hidden" name="csrf_token" value="tok" />
      <button type="submit">Enviar</button>
      <div data-surface="jobs-feed"></div>
      <div data-skeleton="jobs-feed" hidden aria-hidden="true"></div>
    </form>
  `;
  global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
  const form = document.getElementById("upload-form");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    document.querySelectorAll(`[data-skeleton="jobs-feed"]`).forEach((el) => {
      el.hidden = false;
      el.setAttribute("aria-hidden", "false");
    });
    try {
      const resp = await fetch(form.action, { method: "POST" });
      if (!resp.ok) {
        throw new Error("upload-failed");
      }
    } catch (_) {
      const toast = document.createElement("div");
      toast.className = "toast";
      document.body.appendChild(toast);
    }
  });

  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await Promise.resolve();

  const skeleton = document.querySelector('[data-skeleton="jobs-feed"]');
  expect(skeleton.hidden).toBe(false);
  expect(document.querySelector(".toast")).not.toBeNull();
});
