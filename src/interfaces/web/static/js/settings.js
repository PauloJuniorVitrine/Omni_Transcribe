import { setSurfaceLoading, showToast, appendCsrf, withCsrf } from "./core.js";

function bindAjaxForms() {
  document.querySelectorAll('form[data-ajax="true"]').forEach((form) => {
    const updatedTarget = form.dataset.updatedTarget;
    form.addEventListener("submit", async (event) => {
      if (event.defaultPrevented) {
        return;
      }
      event.preventDefault();
      const surfaceId = form.dataset.loadingSurface || "";
      const submitButton = form.querySelector('[type="submit"]');
      if (submitButton) {
        submitButton.dataset.originalText = submitButton.textContent || "";
        submitButton.textContent = submitButton.getAttribute("data-loading") || "Processando...";
        submitButton.disabled = true;
        submitButton.classList.add("loading");
      }
      if (surfaceId) {
        setSurfaceLoading(surfaceId, true);
      }
      try {
        const endpoint = form.getAttribute("action") || window.location.pathname;
        const method = (form.getAttribute("method") || "post").toUpperCase();
        const formData = new FormData(form);
        appendCsrf(formData);
        const response = await fetch(endpoint, {
          method,
          body: formData,
          headers: withCsrf({
            Accept: "application/json",
            "X-Requested-With": "fetch",
          }),
          credentials: "same-origin",
        });
        if (!response.ok) {
          throw new Error("ajax-failed");
        }
        const payload = await response.json().catch(() => ({}));
        const successMessage =
          form.dataset.successMessage || payload.message || "Operação concluída.";
        showToast(successMessage, "success");
        if (updatedTarget && payload.updated_at_human) {
          document
            .querySelectorAll(`[data-updated-label="${updatedTarget}"]`)
            .forEach((label) => {
              label.textContent = `Atualizado às ${payload.updated_at_human}`;
            });
        }
      } catch (_error) {
        const errorMessage = form.dataset.errorMessage || "Não foi possível completar a ação.";
        showToast(errorMessage, "error");
      } finally {
        if (surfaceId) {
          setSurfaceLoading(surfaceId, false);
        }
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.classList.remove("loading");
          if (submitButton.dataset.originalText) {
            submitButton.textContent = submitButton.dataset.originalText;
          }
        }
      }
    });
  });
}

function bindTemplateActions() {
  const editModal = document.getElementById("template-edit-modal");
  if (!editModal) {
    return;
  }
  const form = editModal.querySelector("[data-template-edit-form]");
  const bodyField = form.querySelector('textarea[name="body"]');
  editModal.querySelectorAll("[data-dismiss-modal]").forEach((el) => {
    el.addEventListener("click", () => editModal.close());
  });
  const localeField = form.querySelector('input[name="locale"]');
  document.querySelectorAll("[data-template-edit]").forEach((button) => {
    button.addEventListener("click", async () => {
      const templateId = button.dataset.templateEdit;
      if (!templateId) {
        return;
      }
      const response = await fetch(`/settings/templates/${templateId}/raw`, {
        headers: withCsrf({ Accept: "application/json", "X-Requested-With": "fetch" }),
      }).catch(() => null);
      const payload = await response?.json().catch(() => null);
      if (!payload) {
        showToast("Não foi possível carregar o template.", "error");
        return;
      }
      form.querySelector('input[name="template_id"]').value = templateId;
      form.querySelector('input[name="name"]').value =
        button.dataset.templateName || payload.name || "";
      form.querySelector('input[name="description"]').value =
        button.dataset.templateDescription || payload.description || "";
      localeField.value = button.dataset.templateLocale || payload.locale || "";
      bodyField.value = payload.body || "";
      editModal.showModal();
    });
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    appendCsrf(formData);
    const templateId = formData.get("template_id");
    const response = await fetch(`/settings/templates/${templateId}/update`, {
      method: "POST",
      body: formData,
      headers: { Accept: "application/json", "X-Requested-With": "fetch" },
    });
    if (!response.ok) {
      showToast("Não foi possível atualizar o template.", "error");
      return;
    }
    showToast("Template atualizado com sucesso.", "success");
    window.location.reload();
  });
  document.querySelectorAll("[data-template-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      const templateId = button.dataset.templateDelete;
      if (!templateId || !window.confirm("Remover este template?")) {
        return;
      }
      const response = await fetch(`/settings/templates/${templateId}`, {
        method: "DELETE",
        headers: withCsrf({ "X-Requested-With": "fetch" }),
      });
      if (!response.ok) {
        showToast("Não foi possível remover o template.", "error");
        return;
      }
      document.querySelector(`[data-template-row="${templateId}"]`)?.remove();
      showToast("Template removido.", "success");
    });
  });

  document.querySelectorAll("[data-template-preview]").forEach((button) => {
    button.addEventListener("click", async () => {
      const mode = button.dataset.templatePreview;
      let formRef;
      if (mode === "create") {
        formRef = document.querySelector('form[action="/settings/templates"]');
      } else if (mode === "edit") {
        formRef = form;
      }
      if (!formRef) {
        return;
      }
      const bodyFieldRef = formRef.querySelector('textarea[name="body"]');
      if (!bodyFieldRef || !bodyFieldRef.value.trim()) {
        showToast("Informe o corpo do template antes de pré-visualizar.", "warning");
        return;
      }
      const previewData = new FormData();
      previewData.append("body", bodyFieldRef.value);
      appendCsrf(previewData);
      try {
        const response = await fetch("/settings/templates/preview", {
          method: "POST",
          body: previewData,
          headers: withCsrf({ "X-Requested-With": "fetch" }),
        });
        if (!response.ok) {
          throw new Error("preview-failed");
        }
        const payload = await response.json();
        const target = document.querySelector(
          `[data-template-preview-output="${mode}"]`
        );
        if (target) {
          target.textContent = payload.rendered || "Prévia indisponível.";
        }
      } catch (_error) {
        showToast("Falha ao gerar prévia.", "error");
      }
    });
  });
}

export function initSettings() {
  bindAjaxForms();
}

export function initTemplateSettings() {
  bindTemplateActions();
}
