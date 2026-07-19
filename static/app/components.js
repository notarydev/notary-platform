/**
 * Notary Platform — shared UI primitives.
 *
 * No alert() / prompt(). Everything renders inside the app surface.
 */

/* global S */

function renderDrawer(title, body, actions = "") {
  const id = "drawer-" + Math.random().toString(36).slice(2, 9);
  const el = document.createElement("div");
  el.id = id;
  el.className = "drawer-overlay";
  el.innerHTML = `
    <div class="drawer" onclick="event.stopPropagation()">
      <div class="drawer-header">
        <span class="drawer-title">${esc(title)}</span>
        <button class="btn btn-sm btn-outline" data-close>✕</button>
      </div>
      <div class="drawer-body">${body}</div>
      ${actions ? `<div class="drawer-actions">${actions}</div>` : ""}
    </div>`;
  el.addEventListener("click", (e) => {
    if (e.target === el) closeDrawer(id);
  });
  el.querySelector("[data-close]")?.addEventListener("click", () => closeDrawer(id));
  document.body.appendChild(el);
  return id;
}

function closeDrawer(id) {
  const el = typeof id === "string" ? document.getElementById(id) : id;
  if (el) el.remove();
}

function renderModal(title, body, actions = "") {
  return renderDrawer(title, body, actions);
}

function renderStatusBadge(status, text) {
  const map = {
    pass: "badge-certified",
    ready: "badge-certified",
    healthy: "badge-certified",
    complete: "badge-certified",
    warn: "badge-mitigated",
    warning: "badge-mitigated",
    fail: "badge-red",
    failed: "badge-red",
    blocked: "badge-red",
    not_started: "badge-planned",
    running: "badge-replayable",
    planned: "badge-planned",
    unknown: "badge-planned",
  };
  const cls = map[status] || "badge-ingested";
  return `<span class="badge ${cls}">${esc(text || status)}</span>`;
}

function renderWorkflowStep(label, state, detail, actionHtml) {
  const colors = {
    complete: "var(--green)",
    ready: "var(--green)",
    pass: "var(--green)",
    running: "var(--accent)",
    warn: "var(--amber)",
    warning: "var(--amber)",
    fail: "var(--red)",
    failed: "var(--red)",
    blocked: "var(--red)",
    not_started: "var(--dim)",
    planned: "var(--dim)",
    unknown: "var(--dim)",
  };
  const color = colors[state] || colors.unknown;
  const icon = state === "complete" || state === "pass" || state === "ready" ? "✓"
    : state === "running" ? "⟳"
    : state === "warn" || state === "warning" ? "⚠"
    : state === "fail" || state === "failed" || state === "blocked" ? "✗"
    : "○";
  return `
    <div class="workflow-step" data-state="${state}">
      <div class="workflow-step-icon" style="color:${color};border-color:${color}">${icon}</div>
      <div class="workflow-step-body">
        <div class="workflow-step-title" style="color:${color}">${esc(label)}</div>
        ${detail ? `<div class="workflow-step-detail">${detail}</div>` : ""}
        ${actionHtml ? `<div class="workflow-step-action">${actionHtml}</div>` : ""}
      </div>
    </div>`;
}

function renderCodeBlock(code, opts = {}) {
  const id = "code-" + Math.random().toString(36).slice(2, 9);
  return `
    <div class="code-block">
      <pre id="${id}">${esc(code)}</pre>
      ${opts.copy !== false ? `<button class="btn btn-sm btn-outline" onclick="copyToClipboard('${id}', this)">Copy</button>` : ""}
    </div>`;
}

function renderEmptyState(title, detail, actionHtml) {
  return `
    <div class="empty-state">
      <h3>${esc(title)}</h3>
      <p>${esc(detail)}</p>
      ${actionHtml || ""}
    </div>`;
}

function renderErrorState(error, retryAction) {
  return `
    <div class="error-state">
      <p>⚠ ${esc(error)}</p>
      ${retryAction ? `<button class="btn" onclick="${retryAction}">Retry</button>` : ""}
    </div>`;
}

function renderDisabledAction(label, reason) {
  return `<button class="btn btn-sm" disabled title="${esc(reason)}">${esc(label)}</button>`;
}

function renderSection(title, body, opts = {}) {
  return `
    <section>
      <div class="section-title">${esc(title)}</div>
      ${opts.sub ? `<div class="section-sub">${esc(opts.sub)}</div>` : ""}
      ${body}
    </section>`;
}

function renderKV(label, value) {
  return `
    <div class="kv">
      <span class="kv-label">${esc(label)}</span>
      <span class="kv-value">${value}</span>
    </div>`;
}

function renderTable(headers, rows, opts = {}) {
  if (!rows.length) return renderEmptyState("No data", opts.emptyDetail || "Nothing to show yet.", opts.emptyAction);
  return `
    <table>
      <thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((row) => `<tr>${row.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>
    </table>`;
}

function renderFilterPills(pills) {
  return `
    <div class="filter-pills">
      ${pills.map((p) => `<button class="filter-pill${p.active ? " active" : ""}" data-filter="${esc(p.key)}" onclick="${p.onClick}">${esc(p.label)}</button>`).join("")}
    </div>`;
}

function esc(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function copyToClipboard(elementId, btn) {
  const el = document.getElementById(elementId);
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(() => {
    const original = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = original), 1200);
  }).catch(() => {
    btn.textContent = "Copy failed";
  });
}

function notify(message, type = "info") {
  const id = "toast-" + Math.random().toString(36).slice(2, 9);
  const el = document.createElement("div");
  el.id = id;
  el.className = `toast toast-${type}`;
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => {
    el.classList.add("toast-hide");
    setTimeout(() => el.remove(), 300);
  }, 3000);
}
