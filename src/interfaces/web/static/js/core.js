let cachedCsrfToken = null;

const TOAST_PRESETS = {
  success: { icon: "[OK]", title: "Sucesso" },
  error: { icon: "[!]", title: "Erro" },
  warning: { icon: "[!]", title: "Atencao" },
  info: { icon: "[i]", title: "Informacao" },
};

export function getCsrfToken() {
  if (cachedCsrfToken !== null) {
    return cachedCsrfToken;
  }
  const meta = document.querySelector('meta[name="csrf-token"]');
  cachedCsrfToken = meta?.getAttribute("content") || "";
  return cachedCsrfToken;
}

export function withCsrf(headers = {}) {
  const token = getCsrfToken();
  if (token) {
    return { ...headers, "X-CSRF-Token": token };
  }
  return headers;
}

export function appendCsrf(formData) {
  const token = getCsrfToken();
  if (token && !formData.has("csrf_token")) {
    formData.append("csrf_token", token);
  }
  return formData;
}

export function setSurfaceLoading(targetId, isLoading) {
  if (!targetId) {
    return;
  }
  document.querySelectorAll(`[data-skeleton="${targetId}"]`).forEach((element) => {
    element.hidden = !isLoading;
    element.classList.toggle("is-visible", isLoading);
    element.setAttribute("aria-hidden", String(!isLoading));
  });
  document.querySelectorAll(`[data-surface="${targetId}"]`).forEach((surface) => {
    surface.classList.toggle("is-loading", isLoading);
    surface.setAttribute("aria-busy", String(isLoading));
  });
}

export function showToast(message, variant = "info", options = {}) {
  const preset = TOAST_PRESETS[variant] || TOAST_PRESETS.info;
  const toast = document.createElement("div");
  toast.className = `toast toast--${variant}`;
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");

  const iconEl = document.createElement("span");
  iconEl.className = "toast-icon";
  iconEl.textContent = options.icon || preset.icon || "";
  toast.appendChild(iconEl);

  const content = document.createElement("div");
  content.className = "toast-content";
  const titleText = options.title ?? preset.title ?? "";
  if (titleText) {
    const titleEl = document.createElement("strong");
    titleEl.textContent = titleText;
    content.appendChild(titleEl);
  }
  const messageEl = document.createElement("p");
  messageEl.textContent = message;
  content.appendChild(messageEl);
  toast.appendChild(content);

  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("visible"));
  setTimeout(() => {
    toast.classList.remove("visible");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

export function updateLabelState(selector, text, state = "") {
  document.querySelectorAll(selector).forEach((label) => {
    label.textContent = text;
    if (state) {
      label.dataset.state = state;
    } else {
      delete label.dataset.state;
    }
  });
}
