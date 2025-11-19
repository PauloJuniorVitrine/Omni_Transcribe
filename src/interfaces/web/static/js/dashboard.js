import { setSurfaceLoading } from "./core.js";

function bindLiveSummary() {
  const container = document.querySelector("[data-live-summary-endpoint]");
  if (!container) {
    return;
  }
  const endpoint = container.dataset.liveSummaryEndpoint;
  if (!endpoint) {
    return;
  }
  const intervalMs = Math.max(Number(container.dataset.refreshInterval || "30") * 1000, 5000);
  const statusEl = container.querySelector("[data-summary-updated]");
  const surfaceId = container.dataset.loadingSurface || container.dataset.surface || "";
  let hasLoaded = false;

  const updateStatus = (text, state = "") => {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = text;
    if (state) {
      statusEl.dataset.state = state;
    } else {
      delete statusEl.dataset.state;
    }
  };

  const formatPercent = (value) => {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return null;
    }
    return `${(value * 100).toFixed(2)}%`;
  };

  const updateAccuracySummary = (accuracy) => {
    if (!accuracy) {
      return;
    }
    container.querySelectorAll("[data-accuracy-field]").forEach((element) => {
      const field = element.dataset.accuracyField;
      if (!field) {
        return;
      }
      let text = "";
      if (field === "average_score") {
        const percent = formatPercent(accuracy.average_score);
        text = percent ?? "-";
      } else if (field === "average_wer") {
        const percent = formatPercent(accuracy.average_wer);
        text = percent ? `WER médio ${percent}` : "WER médio N/A";
      } else {
        const value = accuracy[field];
        text = typeof value === "number" ? String(value) : String(value || 0);
      }
      element.textContent = text;
    });
  };

  const refresh = async () => {
    if (!hasLoaded && surfaceId) {
      setSurfaceLoading(surfaceId, true);
    }
    try {
      const response = await fetch(endpoint, { headers: { Accept: "application/json" } });
      if (!response.ok) {
        throw new Error("summary-fetch-failed");
      }
      const payload = await response.json();
      if (payload.summary) {
        Object.entries(payload.summary).forEach(([key, value]) => {
          const field = container.querySelector(`[data-summary-field="${key}"]`);
          if (field) {
            field.textContent = value;
          }
        });
      }
      if (payload.accuracy) {
        updateAccuracySummary(payload.accuracy);
      }
      if (payload.generated_at) {
        const updatedAt = new Date(payload.generated_at);
        const formatted = updatedAt.toLocaleTimeString("pt-BR", { hour12: false });
        updateStatus(`Atualizado Ã s ${formatted}`, "success");
      } else {
        updateStatus("AtualizaÃ§Ã£o em tempo real ativa", "success");
      }
      hasLoaded = true;
    } catch (_error) {
      updateStatus("AtualizaÃ§Ã£o em tempo real indisponÃ­vel", "error");
    } finally {
      if (surfaceId) {
        setSurfaceLoading(surfaceId, false);
      }
    }
  };

  refresh();
  const timerId = window.setInterval(() => {
    if (!document.hidden) {
      refresh();
    }
  }, intervalMs);

  window.addEventListener("beforeunload", () => window.clearInterval(timerId));
}

function bindLiveIncidents() {
  const panel = document.querySelector("[data-live-incidents-endpoint]");
  if (!panel) {
    return;
  }
  const endpoint = panel.dataset.liveIncidentsEndpoint;
  if (!endpoint) {
    return;
  }
  const list = panel.querySelector("[data-incident-list]");
  const statusEl = panel.querySelector("[data-incidents-updated]");
  const intervalMs = Math.max(Number(panel.dataset.refreshInterval || "45") * 1000, 10000);
  const emptyLabel = panel.dataset.emptyLabel || "Nenhum incidente registrado.";
  const surfaceId = panel.dataset.loadingSurface || panel.dataset.surface || "";
  let hasLoaded = false;

  const updateStatus = (text, state = "") => {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = text;
    if (state) {
      statusEl.dataset.state = state;
    } else {
      delete statusEl.dataset.state;
    }
  };

  const renderItems = (items) => {
    if (!list) {
      return;
    }
    list.innerHTML = "";
    if (!items.length) {
      const empty = document.createElement("li");
      empty.className = "incident-empty";
      empty.textContent = emptyLabel;
      list.appendChild(empty);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement("li");
      li.className = "incident-item";
      const body = document.createElement("div");
      body.className = "incident-body";
      const level = (item.level || "INFO").toUpperCase();
      const badge = document.createElement("span");
      badge.className = `badge badge-${level}`;
      badge.textContent = `${item.icon || ""} ${level}`.trim();
      const textWrapper = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = item.event || "Evento";
      const message = document.createElement("p");
      message.textContent = item.message || "Sem detalhes adicionais.";
      textWrapper.appendChild(title);
      textWrapper.appendChild(message);
      body.appendChild(badge);
      body.appendChild(textWrapper);
      const meta = document.createElement("div");
      meta.className = "incident-meta";
      const timestamp = document.createElement("span");
      timestamp.textContent = item.timestamp_human || "";
      meta.appendChild(timestamp);
      if (item.job_id) {
        const link = document.createElement("a");
        link.href = `/jobs/${item.job_id}`;
        link.textContent = `Job ${item.job_id}`;
        meta.appendChild(link);
      }
      li.appendChild(body);
      li.appendChild(meta);
      list.appendChild(li);
    });
  };

  const refresh = async () => {
    if (!hasLoaded && surfaceId) {
      setSurfaceLoading(surfaceId, true);
    }
    try {
      const response = await fetch(endpoint, { headers: { Accept: "application/json" } });
      if (!response.ok) {
        throw new Error("incidents-fetch-failed");
      }
      const payload = await response.json();
      renderItems(payload.items || []);
      if (payload.generated_at) {
        const updatedAt = new Date(payload.generated_at);
        const formatted = updatedAt.toLocaleTimeString("pt-BR", { hour12: false });
        updateStatus(`Atualizado Ã s ${formatted}`, "success");
      } else {
        updateStatus("Monitoramento em tempo real ativo", "success");
      }
      hasLoaded = true;
    } catch (_error) {
      updateStatus("Falha ao atualizar incidentes", "error");
    } finally {
      if (surfaceId) {
        setSurfaceLoading(surfaceId, false);
      }
    }
  };

  refresh();
  const timerId = window.setInterval(() => {
    if (!document.hidden) {
      refresh();
    }
  }, intervalMs);
  window.addEventListener("beforeunload", () => window.clearInterval(timerId));
}

export function initDashboard() {
  bindLiveSummary();
  bindLiveIncidents();
}

