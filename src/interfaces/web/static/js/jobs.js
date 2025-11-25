
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
  bindReactiveFilters();
  bindTemplatePreview();
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

const JOBS_ENDPOINT = "/api/dashboard/jobs";
const TEMPLATE_PREVIEW_ENDPOINT = "/api/templates/preview";

function bindReactiveFilters() {
  const form = document.querySelector("form[data-jobs-form]");
  const body = document.querySelector("[data-jobs-body]");
  if (!form || !body) {
    return;
  }
  const filtersMeta = document.querySelector("[data-filters-updated]");
  const paginationControls = document.querySelector("[data-jobs-pagination]");
  const currentPageLabel = paginationControls?.querySelector("[data-current-page]");
  const pageInput = form.querySelector('input[name="page"]');
  const limitInput = form.querySelector('input[name="limit"]');
  const paginationButtons = document.querySelectorAll("[data-page-control]");
  const surfaceId = form.dataset.loadingSurface || "jobs-feed";

  const updateLabel = (text, state) => {
    if (filtersMeta) {
      updateLabelState("[data-filters-updated]", text, state);
    }
  };

  const fetchJobs = async (targetPage = 1) => {
    const params = new URLSearchParams(new FormData(form));
    params.set("page", String(targetPage));
    if (limitInput?.value) {
      params.set("limit", limitInput.value);
    }
    setSurfaceLoading(surfaceId, true);
    updateLabel("Atualizando filtros...", "loading");
    try {
      const response = await fetch(`${JOBS_ENDPOINT}?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error("jobs-fetch-failed");
      }
      const payload = await response.json();
      renderJobsTable(body, payload.jobs);
      updateSummaryFields(payload.summary, payload.accuracy);
      if (pageInput) {
        pageInput.value = String(payload.page);
      }
      updatePaginationState(form, payload, currentPageLabel);
      const generatedLabel = payload.generated_at
        ? `Atualizado as ${new Date(payload.generated_at).toLocaleTimeString("pt-BR", {
            hour12: false,
          })}`
        : "Atualizacao concluida";
      updateLabel(generatedLabel, "success");
    } catch (_error) {
      showToast("Nao foi possivel atualizar os jobs.", "error");
      updateLabel("Falha ao atualizar", "error");
    } finally {
      setSurfaceLoading(surfaceId, false);
    }
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    fetchJobs(1);
  });

  paginationButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const target = button.dataset.pageTarget;
      if (!target) {
        return;
      }
      const numericPage = Number(target);
      if (Number.isNaN(numericPage)) {
        return;
      }
      fetchJobs(numericPage);
    });
  });
}

function renderJobsTable(container, jobs) {
  container.innerHTML = "";
  if (!jobs.length) {
    renderEmptyJobs(container);
    return;
  }
  jobs.forEach((job) => {
    const row = document.createElement("tr");
    row.appendChild(createCell(job.id));
    row.appendChild(createCell(job.source_name));
    row.appendChild(createCell(job.profile_id));
    const statusCell = document.createElement("td");
    const statusBadge = document.createElement("span");
    statusBadge.className = `badge ${statusBadgeClass(job.status)}`;
    statusBadge.textContent = humanizeStatus(job.status);
    statusCell.appendChild(statusBadge);
    row.appendChild(statusCell);
    row.appendChild(createCell(job.language || "-"));
    row.appendChild(renderAccuracyCell(job));
    const actionCell = document.createElement("td");
    const link = document.createElement("a");
    link.href = `/jobs/${job.id}`;
    link.textContent = "Ver detalhes";
    actionCell.appendChild(link);
    row.appendChild(actionCell);
    container.appendChild(row);
  });
}

function renderEmptyJobs(container) {
  container.innerHTML = `
    <tr class="table-empty">
      <td colspan="7">
        <div class="empty-state">
          <div class="empty-icon">OT</div>
          <div>
            <strong>Nenhum job encontrado ainda.</strong>
            <p>Envie um audio na secao "Enviar audio" para comecar.</p>
          </div>
        </div>
      </td>
    </tr>
  `;
}

function createCell(value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  return cell;
}

function renderAccuracyCell(job) {
  const cell = document.createElement("td");
  const status = job.accuracy_status;
  if (status) {
    const badge = document.createElement("span");
    const badgeClass =
      status === "needs_review" ? "badge-warning" : status === "passing" ? "badge-success" : "badge";
    badge.className = `badge ${badgeClass}`;
    badge.textContent = status === "needs_review" ? "Rever" : status === "passing" ? "OK" : humanizeStatus(status);
    badge.setAttribute("aria-label", `Precisao: ${badge.textContent}`);
    cell.appendChild(badge);
    return cell;
  }
  if (job.accuracy_requires_review) {
    const badge = document.createElement("span");
    badge.className = "badge badge-warning";
    badge.textContent = "Revisar";
    badge.setAttribute("aria-label", "Precisao: requer revisao");
    cell.appendChild(badge);
    return cell;
  }
  cell.textContent = "-";
  return cell;
}

function updateSummaryFields(summary = {}, accuracy = {}) {
  Object.entries(summary).forEach(([key, value]) => {
    const target = document.querySelector(`[data-summary-field="${key}"]`);
    if (target) {
      target.textContent = String(value ?? 0);
    }
  });
  const evaluated = document.querySelector(`[data-accuracy-field="evaluated"]`);
  if (evaluated) {
    evaluated.textContent = String(accuracy.evaluated ?? 0);
  }
  const needsReview = document.querySelector(`[data-accuracy-field="needs_review"]`);
  if (needsReview) {
    needsReview.textContent = String(accuracy.needs_review ?? 0);
  }
  const passing = document.querySelector(`[data-accuracy-field="passing"]`);
  if (passing) {
    passing.textContent = String(accuracy.passing ?? 0);
  }
  const scoreLabel = document.querySelector(`[data-accuracy-field="average_score"]`);
  if (scoreLabel) {
    scoreLabel.textContent = formatPercentage(accuracy.average_score);
  }
  const werLabel = document.querySelector(`[data-accuracy-field="average_wer"]`);
  if (werLabel) {
    werLabel.textContent = formatPercentage(accuracy.average_wer);
  }
}

function formatPercentage(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${(value * 100).toFixed(2)}%`;
}

function humanizeStatus(status) {
  if (!status) {
    return "";
  }
  return status
    .replace(/_/g, " ")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function statusBadgeClass(status) {
  switch (status) {
    case "approved":
      return "badge-success";
    case "awaiting_review":
    case "adjustments_required":
      return "badge-warning";
    case "failed":
    case "rejected":
      return "badge-danger";
    case "processing":
    case "asr_completed":
    case "post_editing":
      return "badge-INFO";
    default:
      return "badge";
  }
}

function updatePaginationState(form, payload, label) {
  const prevLink = document.querySelector("[data-page-control='prev']");
  const nextLink = document.querySelector("[data-page-control='next']");
  const prevPage = payload.page > 1 ? payload.page - 1 : null;
  const nextPage = payload.has_more ? payload.page + 1 : null;

  const buildHref = (pageNumber) => {
    if (!pageNumber) {
      return "#";
    }
    const params = new URLSearchParams(new FormData(form));
    params.set("page", String(pageNumber));
    return `/?${params.toString()}`;
  };

  const updateLink = (link, target) => {
    if (!link) {
      return;
    }
    link.dataset.pageTarget = target ? String(target) : "";
    if (target) {
      link.setAttribute("href", buildHref(target));
      link.setAttribute("aria-disabled", "false");
      link.classList.remove("btn--disabled");
    } else {
      link.setAttribute("href", "#");
      link.setAttribute("aria-disabled", "true");
      link.classList.add("btn--disabled");
    }
  };

  updateLink(prevLink, prevPage);
  updateLink(nextLink, nextPage);
  if (label) {
    label.textContent = `Pagina ${payload.page}`;
  }
}

function bindTemplatePreview() {
  const section = document.querySelector("[data-template-preview]");
  if (!section) {
    return;
  }
  const select = section.querySelector("[data-template-selector]");
  const statusLabel = section.querySelector("[data-preview-updated]");
  const output = section.querySelector("[data-template-preview-content]");
  if (!select || !output) {
    return;
  }

  const refreshPreview = async () => {
    output.textContent = "Carregando preview...";
    try {
      const params = new URLSearchParams();
      if (select.value) {
        params.set("template_id", select.value);
      }
      const response = await fetch(`${TEMPLATE_PREVIEW_ENDPOINT}?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error("template-preview-failed");
      }
      const payload = await response.json();
      output.textContent = payload.rendered.trim() || "Sem conteudo para exibir.";
      if (statusLabel) {
        statusLabel.textContent = `Atualizado as ${new Date().toLocaleTimeString("pt-BR", { hour12: false })}`;
      }
    } catch {
      output.textContent = "Falha ao carregar preview.";
      if (statusLabel) {
        statusLabel.textContent = "Preview indisponivel";
      }
    }
  };

  select.addEventListener("change", refreshPreview);
  refreshPreview();
}
