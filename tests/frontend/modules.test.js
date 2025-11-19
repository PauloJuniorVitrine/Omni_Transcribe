global.requestAnimationFrame = (cb) => cb();

test("core exports toast helper", async () => {
  document.body.innerHTML = "";
  const mod = await import("../../src/interfaces/web/static/js/core.js");
  expect(typeof mod.showToast).toBe("function");
  // ensure it can append toasts
  mod.showToast("Teste", "info", { title: "Aviso" });
  expect(document.querySelector(".toast")).not.toBeNull();
});

test("jobs module exposes initializer", async () => {
  const jobs = await import("../../src/interfaces/web/static/js/jobs.js");
  expect(typeof jobs.initJobDetail).toBe("function");
});
