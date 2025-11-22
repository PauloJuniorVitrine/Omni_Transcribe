
import { setSurfaceLoading, showToast, updateLabelState, withCsrf } from "./core.js";

function bindArtifactPreview() {
  const modal = document.getElementById("artifact-modal");
  if (!modal) {
    return;
  }
  const modalDialog = modal.querySelector(".modal-dialog");
  const modalBody = modal.querySelector("[data-modal-content]");
  const modalTitle = modal.querySelector("[data-modal-title]");
  let lastFocusedElement = null;

  const closeModal = () => {
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    if (lastFocusedElement) {
      lastFocusedElement.focus();
    }
  };

  modal.querySelectorAll("[data-dismiss-modal]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });

  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.classList.contains("open")) {
      closeModal();
    }
  });

  document.querySelectorAll("[data-preview-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      const url = button.dataset.previewUrl;
      const extension = (button.dataset.previewExtension || "").toLowerCase();
      const label = button.dataset.previewLabel || "Pre-visualizacao";
      if (!url) {
        return;
      }
      if (!["txt", "srt", "json", "vtt", "csv"].includes(extension)) {
        showToast("Previa nao disponivel para este formato.", "warning");
        return;
      }
      lastFocusedElement = document.activeElement;
      modalTitle.textContent = label;
      modalBody.textContent = "Carregando artefato...";
      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
      modalDialog.focus();
      try {
        const response = await fetch(url, { headers: { Accept: "text/plain" } });
        if (!response.ok) {
          throw new Error("download-failed");
        }
        const text = await response.text();
        modalBody.textContent = text.trim() || "Sem conteudo para exibir.";
      } catch (_error) {
        closeModal();
        showToast("Nao foi possivel carregar o artefato.", "error");
      }
    });
  });
}

function bindProcessActions() {
  document.querySelectorAll("[data-enhanced-process]").forEach((form) => {
    const endpoint = form.dataset.processEndpoint;
    if (!endpoint) {
      return;
    }
    form.addEventListener("submit", async (event) => {
      if (event.defaultPrevented) {
        return;
      }
      event.preventDefault();
      const surfaceId = form.dataset.loadingSurface || "";
      const statusSelector = form.dataset.statusTarget || "[data-process-status]";
      let statusEl =
        form.closest("section")?.querySelector(statusSelector) ||
        document.querySelector(statusSelector);
      const submitButton = form.querySelector('[type="submit"]');
      if (statusEl) {
        statusEl.textContent = "Solicitando processamento...";
        statusEl.dataset.state = "loading";
      }
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.classList.add("loading");
      }
      setSurfaceLoading(surfaceId, true);
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: withCsrf({ Accept: "application/json" }),
          credentials: "same-origin",
        });
        if (!response.ok) {
          throw new Error("process-failed");
        }
        await response.json().catch(() => ({}));
        const successMessage =
          form.dataset.processSuccessLabel || "Processamento assincrono iniciado.";
        const timestamp = new Date().toLocaleTimeString("pt-BR", { hour12: false });
        showToast(successMessage, "success", { title: "Pipeline em execucao" });
        if (statusEl) {
          statusEl.textContent = `${successMessage} (${timestamp})`;
          statusEl.dataset.state = "success";
        }
      } catch (_error) {
        const errorMessage =
          form.dataset.processErrorLabel || "Falha ao iniciar o processamento.";
        showToast(errorMessage, "error", { title: "Erro ao processar" });
        if (statusEl) {
          statusEl.textContent = errorMessage;
          statusEl.dataset.state = "error";
        }
      } finally {
        setSurfaceLoading(surfaceId, false);
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

export function initJobDetail() {
  bindArtifactPreview();
  bindProcessActions();
  bindTemplateSelector();
  bindJobLogs();
}

function bindTemplateSelector() {
  const select = document.querySelector("[data-template-selector]");
  if (!select) {
    return;
  }
  const descriptionEl = document.querySelector("[data-template-description]");
  const updateDescription = () => {
    if (!descriptionEl) {
      return;
    }
    const option = select.selectedOptions[0];
    if (option) {
      descriptionEl.textContent = option.dataset.description || "Sem descricao.";
    }
  };
  select.addEventListener("change", updateDescription);
  updateDescription();
}

function bindJobLogs() {
  const section = document.querySelector("[data-job-logs-endpoint]");
  if (!section) {
    return;
  }
  const list = section.querySelector("[data-log-list]");
  const form = section.querySelector("[data-log-form]");
  const controls = section.querySelector("[data-log-controls]");
  const moreButton = section.querySelector("[data-log-more]");
  const exportButtons = section.querySelectorAll("[data-log-export]");
  const endpoint = section.dataset.jobLogsEndpoint;
  const exportEndpoint = section.dataset.jobLogsExport;
  const statusSelector = "[data-logs-updated]";
  let currentPage = 1;
  let currentFilters = { level: "", event: "" };
  let hasMore = false;

  const renderList = (entries, append = false) => {
    if (!list) {
      return;
    }
    if (!append) {
      list.innerHTML = "";
    }
    if (!entries.length && !append) {
      const empty = document.createElement("li");
      empty.textContent = "Nenhum evento registrado.";
      list.appendChild(empty);
      return;
    }
    entries.forEach((entry) => {
      const li = document.createElement("li");
      li.className = "timeline-item";
      const badge = document.createElement("span");
      badge.className = `badge badge-${(entry.level || "info").toUpperCase()}`;
      badge.textContent = `${(entry.level || "info").toUpperCase()}`;
      const body = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = entry.event || "Evento";
      const message = document.createElement("p");
      message.textContent = entry.message || "Sem detalhes adicionais.";
      const meta = document.createElement("small");
      meta.textContent = entry.timestamp
        ? new Date(entry.timestamp).toLocaleString("pt-BR")
        : "";
      body.appendChild(title);
      body.appendChild(message);
      body.appendChild(meta);
      li.appendChild(badge);
      li.appendChild(body);
      list.appendChild(li);
    });
  };

  const refreshStatus = (text, state) =>
    updateLabelState(statusSelector, text, state);

  const fetchLogs = async (page = 1, append = false) => {
    if (!endpoint) {
      return;
    }
    setSurfaceLoading("logs-timeline", true);
    refreshStatus("Atualizando...", "loading");
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: "20",
        level: currentFilters.level,
        event: currentFilters.event,
      });
      const response = await fetch(`${endpoint}?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error("log-fetch-failed");
      }
      const payload = await response.json();
      const entries = payload.logs || [];
      hasMore = Boolean(payload.has_more);
      currentPage = payload.page;
      renderList(entries, append);
      const labelText = payload.generated_at
        ? `Atualizado as ${new Date(payload.generated_at).toLocaleTimeString("pt-BR", {
            hour12: false,
          })}`
        : "Atualizacao concluida";
      refreshStatus(labelText, "success");
      if (controls) {
        controls.hidden = false;
      }
      if (moreButton) {
        moreButton.hidden = !hasMore;
      }
    } catch (_error) {
      refreshStatus("Falha ao atualizar logs", "error");
      showToast("Nao foi possivel carregar os eventos.", "error");
    } finally {
      setSurfaceLoading("logs-timeline", false);
    }
  };

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    currentFilters = {
      level: form.querySelector('[data-log-filter="level"]')?.value || "",
      event: form.querySelector('[data-log-filter="event"]')?.value || "",
    };
    fetchLogs(1);
  });

  form?.querySelector("[data-log-reset]")?.addEventListener("click", () => {
    form.reset();
    currentFilters = { level: "", event: "" };
    fetchLogs(1);
  });

  moreButton?.addEventListener("click", () => {
    if (hasMore) {
      currentPage += 1;
      fetchLogs(currentPage, true);
    }
  });

  exportButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!exportEndpoint) {
        return;
      }
      const format = button.dataset.logExport || "json";
      const params = new URLSearchParams({
        format,
        level: currentFilters.level,
        event: currentFilters.event,
      });
      window.open(`${exportEndpoint}?${params.toString()}`, "_blank");
    });
  });

  fetchLogs(1);
}
