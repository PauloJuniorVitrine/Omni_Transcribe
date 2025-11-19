import { initGlobal } from "./js/global.js";
import { initDashboard } from "./js/dashboard.js";
import { initJobDetail } from "./js/jobs.js";
import { initSettings, initTemplateSettings } from "./js/settings.js";

document.addEventListener("DOMContentLoaded", () => {
  initGlobal();
  initDashboard();
  initJobDetail();
  initSettings();
  initTemplateSettings();
});
