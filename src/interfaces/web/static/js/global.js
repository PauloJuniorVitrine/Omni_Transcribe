import { setSurfaceLoading, showToast, updateLabelState } from "./core.js";

function bindConfirmForms() {
  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm") || "";
      /* istanbul ignore next */
      if (message && !window.confirm(message)) {
        event.preventDefault();
        return;
      }
      const submitButton = form.querySelector("[data-loading]");
      if (submitButton) {
        submitButton.dataset.originalText = submitButton.textContent || "";
        submitButton.textContent = submitButton.getAttribute("data-loading") || "Processando...";
        submitButton.disabled = true;
        submitButton.classList.add("loading");
      }
    });
  });
}

function bindSurfaceForms() {
  document.querySelectorAll("form[data-loading-surface]").forEach((form) => {
    /* istanbul ignore next */
    if (form.hasAttribute("data-enhanced-process") || form.dataset.ajax === "true") {
      return;
    }
    form.addEventListener(
      "submit",
      (event) => {
        if (event.defaultPrevented) {
          return;
        }
        const surfaceId = form.dataset.loadingSurface;
        setSurfaceLoading(surfaceId, true);
        const labelKey = form.dataset.updatedLabel;
        if (labelKey) {
          updateLabelState(`[data-${labelKey}-updated]`, "Atualizando...", "loading");
        }
      },
      { once: false },
    );
  });
}

function bindSkeletonTriggers() {
  document.querySelectorAll("[data-loading-skeleton]").forEach((trigger) => {
    const eventName = trigger.tagName === "FORM" ? "submit" : "click";
    trigger.addEventListener(eventName, () => {
      const skeletonId = trigger.dataset.loadingSkeleton;
      if (skeletonId) {
        setSurfaceLoading(skeletonId, true);
      }
    });
  });
}

function bindFlashToasts() {
  document.querySelectorAll(".flash[data-toast]").forEach((flash) => {
    const variant = flash.dataset.toastVariant || "info";
    const message = flash.textContent.trim();
    if (message) {
      showToast(message, variant);
    }
  });
}

export function initGlobal() {
  bindConfirmForms();
  bindSurfaceForms();
  bindSkeletonTriggers();
  bindFlashToasts();
}
