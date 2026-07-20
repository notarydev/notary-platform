/**
 * Notary Platform SPA — app shell and view rendering (WO-80).
 *
 * Loads the platform data into guided workflows. No alert() / prompt().
 */

/* global renderDrawer, closeDrawer, renderStatusBadge, renderWorkflowStep, renderCodeBlock, renderEmptyState, renderErrorState, renderDisabledAction, renderSection, renderKV, renderTable, renderFilterPills, esc, notify, copyToClipboard */

const API = "/v1";

const S = {
  env: localStorage.getItem("np-env") || "env:demo",
  view: "home",
  agentVersion: localStorage.getItem("np-agent-version") || "1.2.0",
  token: localStorage.getItem("notaryApiToken") || "",
  authConfigured: null,
  selectedVR: null,
  selectedIncident: null,
  selectedSystem: null,
  selectedProof: null,
  selectedScenario: null,
  selectedReadinessCheck: null,
  selectedReleaseGate: null,
  loading: false,
  error: null,
};

function q(s) { return document.querySelector(s); }
function qa(s) { return document.querySelectorAll(s); }

function _token() {
  return S.token;
}

function authHeaders() {
  const h = {"Content-Type": "application/json"};
  if (_token()) h.Authorization = "Bearer " + _token();
  return h;
}

async function apiGet(path, opts = {}) {
  const url = path + (path.includes("?") ? "&" : "?") + "environment_id=" + encodeURIComponent(S.env);
  const res = await fetch(url, {headers: authHeaders(), ...opts});
  if (res.status === 401) {
    S.authConfigured = true;
    renderAuthPanel();
    throw new Error("Authentication required. Enter your API token in Settings.");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

async function apiPost(path, body, opts = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body || {}),
    ...opts,
  });
  if (res.status === 401) {
    S.authConfigured = true;
    renderAuthPanel();
    throw new Error("Authentication required. Enter your API token in Settings.");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

async function apiPostForm(path, params, opts = {}) {
  const url = path + "?" + new URLSearchParams(params).toString();
  return apiPost(url, {}, opts);
}

async function apiPatch(path, body, opts = {}) {
  const res = await fetch(path, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(body || {}),
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

// --- Navigation ---

function setupNav() {
  qa(".nav-item[data-view]").forEach((el) => {
    el.addEventListener("click", () => {
      qa(".nav-item[data-view]").forEach((x) => x.classList.remove("active"));
      el.classList.add("active");
      S.view = el.dataset.view;
      R();
    });
  });
}

function switchEnv(v) {
  S.env = v;
  localStorage.setItem("np-env", v);
  R();
}

function switchAgentVersion(v) {
  S.agentVersion = v;
  localStorage.setItem("np-agent-version", v);
}

function nav(v) {
  S.view = v;
  qa(".nav-item[data-view]").forEach((x) => x.classList.remove("active"));
  const b = q(`.nav-item[data-view="${v}"]`);
  if (b) b.classList.add("active");
  R();
}

function navWithParam(v, param) {
  S.view = v;
  if (param.vr) S.selectedVR = param.vr;
  if (param.incident) S.selectedIncident = param.incident;
  if (param.system) S.selectedSystem = param.system;
  if (param.proof) S.selectedProof = param.proof;
  if (param.scenario) S.selectedScenario = param.scenario;
  if (param.readinessCheck) S.selectedReadinessCheck = param.readinessCheck;
  if (param.releaseGate) S.selectedReleaseGate = param.releaseGate;
  qa(".nav-item[data-view]").forEach((x) => x.classList.remove("active"));
  const b = q(`.nav-item[data-view="${v}"]`);
  if (b) b.classList.add("active");
  R();
}

// --- Auth panel ---

function renderAuthPanel() {
  const c = q("#content");
  c.innerHTML = `
    <div class="auth-panel">
      <h3>Authentication required</h3>
      <p>/health, /app, and /cc are public. /v1 endpoints require an API token.</p>
      <div class="np-form">
        <div class="np-field">
          <label>API Token</label>
          <input type="text" id="auth-token" placeholder="ntry-..." value="${esc(S.token)}">
        </div>
        <button class="btn" onclick="saveAuthToken()">Save Token</button>
      </div>
    </div>`;
}

function saveAuthToken() {
  const val = q("#auth-token").value.trim();
  S.token = val;
  localStorage.setItem("notaryApiToken", val);
  S.authConfigured = null;
  R();
}

// --- Main render ---

async function R() {
  const c = q("#content");
  c.innerHTML = sk(120) + sk(80);
  q("#view-title").textContent = viewTitle(S.view);
  const isDemo = S.env === "env:demo";
  q("#demo-banner").classList.toggle("hidden", !isDemo);
  q("#global-demo").classList.toggle("hidden", !isDemo);
  q("#env-select").value = S.env;
  q("#agent-version").value = S.agentVersion;

  try {
    if (S.view === "home") {
      const h = await apiGet("/v1/platform/home");
      renderHome(c, h);
    } else if (S.view === "setup") {
      renderSetup(c);
    } else if (S.view === "verification-records") {
      const vrs = await apiGet("/v1/verification-records");
      renderVRs(c, vrs);
    } else if (S.view === "vr-detail") {
      const v = await apiGet("/v1/verification-records/" + S.selectedVR);
      renderVRDetail(c, v);
    } else if (S.view === "incidents") {
      const ix = await apiGet("/v1/incidents");
      renderIncidents(c, ix);
    } else if (S.view === "incident-detail") {
      const i = await apiGet("/v1/incidents/" + S.selectedIncident);
      const wf = await apiGet("/v1/incidents/" + S.selectedIncident + "/workflow");
      renderIncidentDetail(c, i, wf);
    } else if (S.view === "proofs") {
      const proofs = await apiGet("/v1/proofs");
      renderProofs(c, proofs);
    } else if (S.view === "proof-detail") {
      const p = await apiGet("/v1/proofs/" + S.selectedProof);
      renderProofDetail(c, p);
    } else if (S.view === "systems") {
      const systems = await apiGet("/v1/platform/org/systems");
      renderSystems(c, systems);
    } else if (S.view === "system-detail") {
      const s = await apiGet("/v1/platform/org/systems/" + S.selectedSystem);
      const vrs = await apiGet("/v1/verification-records");
      renderSystemDetail(c, s, vrs);
    } else if (S.view === "scenarios") {
      const scenarios = await apiGet("/v1/scenarios");
      const candidates = await apiGet("/v1/scenario-candidates");
      renderScenarios(c, scenarios, candidates);
    } else if (S.view === "scenario-detail") {
      const s = await apiGet("/v1/scenarios/" + S.selectedScenario);
      const runs = await apiGet("/v1/scenario-runs");
      renderScenarioDetail(c, s, runs);
    } else if (S.view === "readiness") {
      const policies = await apiGet("/v1/readiness-policies");
      const checks = await apiGet("/v1/readiness-checks");
      renderReadiness(c, policies, checks);
    } else if (S.view === "readiness-detail") {
      const check = await apiGet("/v1/readiness-checks/" + S.selectedReadinessCheck);
      renderReadinessDetail(c, check);
    } else if (S.view === "release-gate-detail") {
      const gate = await apiGet("/v1/release-gate/checks/" + S.selectedReleaseGate);
      renderReleaseGateDetail(c, gate);
    } else if (S.view === "governance") {
      const vrs = await apiGet("/v1/verification-records");
      renderGovernance(c, vrs);
    } else if (S.view === "settings") {
      renderSettings(c);
    } else {
      c.innerHTML = renderErrorState("Unknown view: " + S.view);
    }
  } catch (e) {
    c.innerHTML = renderErrorState(e.message, "R()");
  }
}

  function viewTitle(v) {
  const titles = {
    home: "Home",
    setup: "Setup",
    "verification-records": "Verification Records",
    "vr-detail": "Verification Record Detail",
    incidents: "Incidents",
    "incident-detail": "Incident Detail",
    proofs: "Proofs",
    "proof-detail": "Proof Detail",
    systems: "Systems",
    "system-detail": "System Detail",
    scenarios: "Scenarios",
    "scenario-detail": "Scenario Detail",
    readiness: "Readiness",
    "readiness-detail": "Readiness Check Detail",
    "release-gate-detail": "Release Gate Detail",
    governance: "Governance",
    settings: "Settings",
  };
  return titles[v] || v;
}

function sk(h) { return `<div class="skeleton" style="height:${h}px;margin-bottom:12px"></div>`; }
function badgeDemo() { return S.env === "env:demo" ? '<span class="badge badge-demo">DEMO</span>' : ""; }
function badgePlanned() { return '<span class="badge badge-planned">PLANNED</span>'; }

function statusBadge(st) { return renderStatusBadge(st, st.replace(/_/g, " ")); }

function chip(n, l, color, view) {
  return `<div class="queue-chip" onclick="nav('${view}')" style="border-left:3px solid var(${color})"><div class="queue-count" style="color:var(${color})">${n}</div><div class="queue-label">${esc(l)}</div></div>`;
}

// --- HOME ---

function renderHome(c, h) {
  q("#org-name").textContent = h.org_id || "Organization";
  const sh = h.setup_health || {};
  const qu = h.queues || {};
  const pf = h.recent_proofs || [];
  const na = h.next_action;
  const blockers = h.blockers || [];

  const stats = [
    ["var(--green)", "✓", sh.sdk_installed ? "Yes" : "No", "SDK Installed"],
    ["var(--accent)", "◆", sh.agents_instrumented || 0, "Agents"],
    ["var(--purple)", "◎", `${sh.systems_connected || 0}/${sh.systems_total || 0}`, "Systems"],
    ["var(--blue)", "◈", sh.capture_policies || 0, "Policies"],
    ["var(--amber)", "⚠", h.vrs_requires_label || 0, "Need Label"],
    ["var(--green)", "✓", h.proofs_issued || 0, "Proofs"],
  ];

  c.innerHTML = `
    ${h.is_demo ? `<div style="margin-bottom:16px;font-size:12px;color:var(--amber);font-weight:600">${badgeDemo()} Demo data — design partner preview</div>` : ""}
    <div class="stat-grid">${stats.map(s => `
      <div class="stat">
        <div style="color:${s[0]};font-size:12px;font-weight:700;margin-bottom:4px">${s[1]}</div>
        <div class="stat-val" style="color:${s[0]}">${s[2]}</div>
        <div class="stat-label">${s[3]}</div>
      </div>`).join("")}
    </div>
    <div class="section-title">Active Queues</div>
    <div class="queue-row">
      ${chip(qu.needs_replay || 0, "Need replay", "--red", "incidents")}
      ${chip(qu.needs_verification || 0, "Need verification", "--amber", "incidents")}
      ${chip(qu.proofs_ready || 0, "Proofs ready", "--green", "proofs")}
      ${chip(qu.needs_label || 0, "Need label", "--amber", "verification-records")}
      ${chip(qu.needs_sandbox || 0, "Need sandbox", "--red", "systems")}
    </div>
    ${blockers.length ? renderSection("Current Blockers", blockers.map(b => `
      <div class="int-card">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div><h4>${esc(b.type.replace(/_/g, " "))}</h4><p>${esc(b.next_action)}</p></div>
          <span class="badge badge-red">${b.count}</span>
        </div>
      </div>`).join("")) : ""}
    ${pf.length ? renderSection("Recent Proofs", `<div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius)">${pf.map(p => `
      <div style="padding:10px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;font-size:12px">
        <span style="font-weight:700;color:var(--text)">${p.incident_id}</span>
        <span class="badge badge-certified">certified</span>
      </div>`).join("")}</div>`) : ""}
    ${na ? `
      <div class="section-title">Next Best Action</div>
      <div class="next-action-card" onclick="nav('${na.view || "incidents"}')${na.vr_id ? `;setTimeout(()=>openVRDetail('${na.vr_id}'),200)` : ""}${na.incident_id ? `;setTimeout(()=>openIncidentDetail('${na.incident_id}'),200)` : ""}">
        <div class="title">${esc(na.label)}</div>
        <div class="detail">Click to open the workflow</div>
      </div>` : ""}
  `;
}

// --- SETUP ---

async function renderSetup(c) {
  c.innerHTML = sk(40);
  const adapters = await apiGet("/v1/platform/adapters").catch(() => []);
  c.innerHTML = `
    <div class="section-title">Get Started</div>
    <div class="section-sub">Your API token is already configured. Use it in API calls and SDK setup.</div>
    <div class="int-card" style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><h4>API Token</h4><p style="font-size:12px;color:var(--muted)">Sent automatically in headers. Copy for CLI/curl use.</p></div>
        <span class="badge badge-built">ACTIVE</span>
      </div>
      ${renderCodeBlock(S.token || "ntry-demo-...")}
      <div style="font-size:11px;color:var(--muted);margin-top:4px">Change or view in <span class="link" onclick="nav('settings')">Settings</span></div>
    </div>
    <div class="section-title">Connect Your AI System</div>
    <div class="section-sub">Choose an integration path. Each card opens a guided setup workflow.</div>
    ${setupCard("python_sdk", "Python SDK", "Best for Python agents and custom workflows.", "built", `pip install -e packages/notary-sdk-py`, [
      {label: "Install Instructions", action: "openSDKSetup()", primary: true},
      {label: "Send Test Capture", action: "sendSDKTestCapture()", primary: false},
    ])}
    ${setupCard("api_submission", "API Submission", "Send JSON Verification Records from any backend.", "built", null, [
      {label: "Open API Guide", action: "openAPISubmissionSetup()", primary: true},
      {label: "Send Sample Record", action: "sendAPISampleRecord()", primary: false},
    ])}
    ${setupCard("manual_submission", "Manual Submission", "Submit overrides, complaints, or disputes by hand.", "built", null, [
      {label: "Submit Manual Record", action: "openManualSubmissionForm()", primary: true},
    ])}
    ${setupCard("webhook", "Webhook", "POST events from support systems or workflow tools.", "built", null, [
      {label: "Configure Webhook", action: "openWebhookSetup()", primary: true},
      {label: "Send Test Event", action: "sendWebhookTestEvent()", primary: false},
    ])}
    ${setupCard("batch_import", "Batch Import", "Import historical data via CSV/JSONL.", "planned", null, [
      {label: "Planned", action: "", primary: false, disabled: true, reason: "Planned for future release. Use API or manual submission today."},
    ])}
    ${setupCard("trace_import", "Trace Import", "Ingest OpenTelemetry/OpenInference traces.", "planned", null, [
      {label: "Planned", action: "", primary: false, disabled: true, reason: "Planned for future release. Use SDK or API submission today."},
    ])}
    <div class="section-title" style="margin-top:24px">Capture Adapter Registry</div>
    <div class="section-sub">What capture methods are available today vs planned</div>
    ${renderTable(["Adapter", "Status", "Description"], adapters.map(ad => [
      `<span style="font-weight:700;color:var(--text)">${ad.label}</span>`,
      statusBadge(ad.status),
      `<span style="font-size:11px">${esc(ad.desc)}</span>`,
    ]), {emptyDetail: "Adapter registry unavailable"})}
  `;
}

function setupCard(id, title, desc, status, code, actions) {
  const isBuilt = status === "built";
  const actionHtml = actions.map(a => {
    if (a.disabled) return renderDisabledAction(a.label, a.reason);
    const cls = a.primary ? "btn btn-sm" : "btn btn-sm btn-outline";
    return `<button class="${cls}" onclick="${a.action}">${esc(a.label)}</button>`;
  }).join("");
  return `
    <div class="int-card">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><h4>${esc(title)}</h4><p>${esc(desc)}</p></div>
        <span class="badge badge-${isBuilt ? "built" : "planned"}">${isBuilt ? "BUILT" : "PLANNED"}</span>
      </div>
      ${code ? renderCodeBlock(code) : ""}
      <div class="action-row" style="margin-top:12px">${actionHtml}</div>
    </div>`;
}

function openSDKSetup() {
  const body = `
    <div class="section-title">1. Install (local / Git path)</div>
    ${renderCodeBlock("git clone https://github.com/notarydev/notary-platform.git\ncd notary-platform\npip install -e packages/notary-sdk-py")}
    <div style="font-size:11px;color:var(--amber);margin:4px 0 12px">Notary Python SDK is not published to PyPI yet. Install from the repo directly.</div>
    <div class="section-title">2. Configure environment</div>
    ${renderCodeBlock(`NOTARY_API_URL=http://localhost:8000\nNOTARY_API_TOKEN=your-token-here`)}
    <div class="section-title">3. Capture a decision</div>
    ${renderCodeBlock(`from notary_sdk import RunCapture\n\ncapture = RunCapture(secret_key=b"your-secret-key")\ncapture.capture_llm(prompt="loan app #1234", response="score: 620")\ncapture.capture_tool(method="POST", url="/score", response={"score": 620})\ncapture.capture_decision(decision="DENY")\nsnapshot = capture.finalize()`)}
    <div class="section-title">4. Submit to Notary</div>
    ${renderCodeBlock(`import requests\nrequests.post(\n  "http://localhost:8000/v1/incidents/ingest",\n  headers={"Authorization": "Bearer your-token-here"},\n  json={"snapshot": snapshot.to_dict()}\n)`)}
  `;
  renderDrawer("Python SDK Setup", body);
}

async function sendSDKTestCapture() {
  try {
    const snapshot = {
      schema_version: 1,
      timestamp: new Date().toISOString(),
      elements: [
        {kind: "llm", payload: {prompt: "loan app demo", response: "score: 620"}},
        {kind: "http", payload: {request: {method: "POST", url: "/score"}, response: {score: 620}, status: 200}},
        {kind: "decision", payload: {decision: "DENY"}},
      ],
      merkle_chain: [],
      root_hash: "demo-root-hash",
    };
    const r = await apiPost("/v1/incidents/ingest", {snapshot});
    notify("Created SDK Verification Record " + r.incident_id, "success");
    nav("verification-records");
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

function openAPISubmissionSetup() {
  const body = `
    <div class="section-title">Endpoint</div>
    ${renderCodeBlock("POST https://api.getnotary.ai/v1/verification-records")}
    <div class="section-title">Auth header</div>
    ${renderCodeBlock("Authorization: Bearer <token>")}
    <div class="section-title">Sample payload — lending</div>
    ${renderCodeBlock(`{\n  "source_type": "api_submission",\n  "external_ref": "APP-A-1234",\n  "agent_id": "agent:lending",\n  "business_function": "loan_underwriting"\n}`)}
    <div class="section-title">Success response</div>
    ${renderCodeBlock(`{\n  "id": "vr-abc123",\n  "replayability": "requires_human_label",\n  "next_action": "Add expected outcome label"\n}`)}
  `;
  renderDrawer("API Submission Guide", body);
}

async function sendAPISampleRecord() {
  try {
    const r = await apiPostForm("/v1/verification-records", {source_type: "api_submission", external_ref: "APP-DEMO-" + Date.now(), agent_id: "agent:lending", business_function: "loan_underwriting"});
    notify("Created API Verification Record " + r.id, "success");
    nav("verification-records");
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

function openManualSubmissionForm() {
  const body = `
    <div class="np-form">
      <div class="np-field"><label>Source System</label><input id="ms-system" value="sys:support-ticketing"></div>
      <div class="np-field"><label>Source Record Ref</label><input id="ms-ref" value="TKT-DEMO-" placeholder="e.g. TKT-1234"></div>
      <div class="np-field"><label>Agent</label><input id="ms-agent" value="agent:support-handoff"></div>
      <div class="np-field"><label>Expected Outcome</label><input id="ms-outcome" value="ESCALATE_TO_HUMAN" placeholder="e.g. ESCALATE_TO_HUMAN"></div>
      <div class="np-field"><label>Reason / Evidence Summary</label><textarea id="ms-transcript">Customer complained about repeated bot responses without escalation.</textarea></div>
    </div>
  `;
  const actions = `<button class="btn" onclick="submitManualForm()">Submit Manual Record</button>`;
  renderDrawer("Manual Submission", body, actions);
}

async function submitManualForm() {
  try {
    const r = await apiPost("/v1/verification-records/manual", {
      ticket_id: q("#ms-ref").value,
      transcript: q("#ms-transcript").value,
      decision: "REVIEW",
      agent_id: q("#ms-agent").value,
      business_function: "support",
      source_system_id: q("#ms-system").value,
    });
    notify("Submitted " + r.id, "success");
    closeDrawer();
    nav("verification-records");
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

function openWebhookSetup() {
  const body = `
    <div class="section-title">Webhook URL</div>
    ${renderCodeBlock("POST https://api.getnotary.ai/v1/verification-records/webhook")}
    <div class="section-title">Auth header</div>
    ${renderCodeBlock("Authorization: Bearer <token>\nX-Webhook-Secret: <secret>")}
    <div class="section-title">Event schema</div>
    ${renderCodeBlock(`{\n  "source_id": "TKT-1234",\n  "events": [\n    {"kind": "model_call", "payload": {"model": "support-agent"}},\n    {"kind": "decision", "payload": {"decision": "CONTINUE_BOT"}}\n  ]\n}`)}
    <div class="section-title">Idempotency</div>
    <p style="font-size:12px;color:var(--muted)">Re-send the same source_id within 24h and Notary deduplicates based on source record reference.</p>
  `;
  renderDrawer("Webhook Setup", body);
}

async function sendWebhookTestEvent() {
  try {
    const r = await apiPost("/v1/verification-records/webhook", {
      source_id: "WEBHOOK-DEMO-" + Date.now(),
      events: [
        {kind: "model_call", payload: {model: "support-agent", intent: "billing dispute"}},
        {kind: "decision", payload: {decision: "CONTINUE_BOT"}},
      ],
    });
    notify("Created webhook V.R. " + r.id, "success");
    nav("verification-records");
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

// --- VERIFICATION RECORDS ---

function renderVRs(c, vrs) {
  if (!vrs.length) {
    c.innerHTML = renderEmptyState("No Verification Records", "Submit a record from Setup or run the demo catalog.", `<button class="btn" onclick="seedDemo()">Seed Demo Data</button>`);
    return;
  }
  const counts = {
    all: vrs.length,
    replayable: vrs.filter(v => v.replayability === "replayable").length,
    partially_replayable: vrs.filter(v => v.replayability === "partially_replayable").length,
    requires_human_label: vrs.filter(v => v.replayability === "requires_human_label").length,
    requires_sandbox: vrs.filter(v => v.replayability === "requires_sandbox").length,
    evidence_only: vrs.filter(v => v.replayability === "evidence_only").length,
    missing_context: vrs.filter(v => v.replayability === "missing_context").length,
  };
  const pills = Object.keys(counts).map(k => ({key: k, label: k.replace(/_/g, " ").replace(/\b\w/g, x => x.toUpperCase()) + " (" + counts[k] + ")", active: false, onClick: `filterVR('${k}')`}));
  c.innerHTML = `
    <div class="section-title">Verification Records</div>
    <div class="section-sub">Intake investigation workspace — source, systems, replayability, labels, next action.</div>
    ${renderFilterPills(pills)}
    <table>
      <thead><tr><th>ID</th><th>Source</th><th>System</th><th>Score</th><th>Replayability</th><th>Label</th><th>Next Action</th><th>Actions</th></tr></thead>
      <tbody>${vrs.map(v => `
        <tr class="vr-row" data-rp="${esc(v.replayability)}">
          <td>${v.is_demo ? badgeDemo() : ""} <span class="link" onclick="openVRDetail('${v.id}')">${v.id}</span></td>
          <td><span class="badge badge-${v.source_type === "sdk_snapshot" ? "built" : "ingested"}">${v.source_type.replace(/_/g, " ")}</span></td>
          <td>${esc(v.source_system_id || "—")}</td>
          <td><span style="font-weight:800;color:${(v.replayability_score || 0) >= 0.8 ? 'var(--green)' : (v.replayability_score || 0) >= 0.5 ? 'var(--amber)' : 'var(--red)'}">${Math.round((v.replayability_score || 0) * 100)}%</span></td>
          <td>${statusBadge(v.replayability)}</td>
          <td>${v.current_label_id ? '✓' : v.replayability === "requires_human_label" ? '<span class="badge badge-planned">needs label</span>' : '—'}</td>
          <td style="font-size:11px">${esc(v.next_action || "—")}</td>
          <td class="action-row">
            ${v.replayability === "requires_human_label" ? `<button class="btn btn-sm btn-amber" onclick="openAddLabelForm('${v.id}')">Add Label</button>` : ""}
            ${v.replayability === "replayable" || v.replayability === "partially_replayable" ? `<button class="btn btn-sm" onclick="runVRReplay('${v.id}')">Replay</button>` : ""}
            ${v.replayability === "replayable" && v.current_label_id ? `<button class="btn btn-sm btn-green" onclick="promoteVR('${v.id}')">Promote</button>` : ""}
            ${v.replayability === "evidence_only" || v.replayability === "missing_context" ? `<button class="btn btn-sm btn-outline" onclick="openVRDetail('${v.id}')">Investigate</button>` : ""}
            <button class="btn btn-sm btn-outline" onclick="openVRDetail('${v.id}')">Detail</button>
          </td>
        </tr>`).join("")}
      </tbody>
    </table>
  `;
  // Default filter 'all' visible; filterVR toggles rows.
  window._vrFilter = "all";
}

function filterVR(s) {
  window._vrFilter = s;
  qa(".vr-row").forEach(r => r.classList.toggle("hidden", s !== "all" && r.dataset.rp !== s));
  qa(".filter-pill").forEach(p => p.classList.toggle("active", p.dataset.filter === s));
}

function openVRDetail(vrId) {
  S.selectedVR = vrId;
  nav("vr-detail");
}

async function renderVRDetail(c, v) {
  const label = v.current_label_id ? await apiGet("/v1/verification-records/" + v.id + "/label").catch(() => null) : null;
  const history = await apiGet("/v1/verification-records/" + v.id + "/label-history").catch(() => ({labels: []}));
  const preflight = await apiGet("/v1/verification-records/" + v.id + "/replay-preflight").catch(() => null);
  const suggestions = v.suggested_labels || [];

  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('verification-records')">← Back to Records</button>
    ${badgeDemo()}
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      ${statusBadge(v.replayability)}
      <span style="font-size:13px;color:var(--muted)">ID: ${v.id}</span>
    </div>
    ${renderSection("Summary", `
      ${renderKV("Source Type", v.source_type)}
      ${renderKV("Source System", v.source_system_id || "—")}
      ${renderKV("Source Record Ref", v.source_record_ref || "—")}
      ${renderKV("Agent", v.agent_id || "—")}
      ${renderKV("Agent Version", v.agent_version || "—")}
      ${renderKV("Model", (v.model_name || "—") + (v.model_provider ? " via " + v.model_provider : ""))}
      ${renderKV("Policy Version", v.policy_version || "—")}
      ${renderKV("Capture Policy", v.capture_policy_id || "—")}
    `)}
    ${renderSection("Replayability", `
      ${renderKV("Score", `<span style="font-weight:800;color:${(v.replayability_score || 0) >= 0.8 ? 'var(--green)' : (v.replayability_score || 0) >= 0.5 ? 'var(--amber)' : 'var(--red)'}">${Math.round((v.replayability_score || 0) * 100)}%</span>`)}
      ${renderKV("State", statusBadge(v.replayability))}
      ${renderKV("Reason", v.replayability_reason || "—")}
      ${renderKV("Missing Prerequisites", (v.missing_prerequisites || []).join(", ") || "None")}
      ${renderKV("Defensibility", v.defensibility_summary || "—")}
      ${preflight ? renderSection("Preflight", `
        <div style="margin:8px 0">${renderStatusBadge(preflight.preflight_status.toLowerCase(), preflight.preflight_status)}</div>
        ${preflight.blocking_factors.length ? `<div class="section-sub">Blocking factors</div>${preflight.blocking_factors.map(f => `<div class="kv"><span class="kv-label">${f.component}</span><span class="kv-value">${f.description}</span></div>`).join("")}` : ""}
        ${preflight.warnings.length ? `<div class="section-sub">Warnings</div>${preflight.warnings.map(w => `<div class="kv"><span class="kv-label">${w.component}</span><span class="kv-value">${w.description}</span></div>`).join("")}` : ""}
        ${preflight.can_proceed ? `<button class="btn btn-sm" onclick="promoteVR('${v.id}')">Promote to Incident</button>` : `<div class="badge badge-red">Cannot promote until blockers resolved</div>`}
      `) : ""}
    `)}
    ${renderSection("Event Timeline", (v.events || []).length ? `
      ${v.events.map((e, idx) => `
        <div class="kv">
          <span class="kv-label">${idx + 1}. ${e.kind}</span>
          <span class="kv-value" style="font-size:11px;font-family:monospace">${JSON.stringify(e.payload).substring(0, 120)}</span>
        </div>
      `).join("")}
    ` : "No events")}
    ${renderSection("Label", `
      ${renderKV("Current Label", label ? `${label.expected_outcome} <span class="badge badge-built">${label.status}</span>` : "—")}
      ${renderKV("Label Source", v.label_source || "—")}
      ${label ? renderKV("Reviewer / Role", `${label.reviewer} / ${label.role}`) : ""}
      ${label ? renderKV("Reason", label.reason) : ""}
      ${suggestions.length ? `<div class="section-sub">Suggested Labels</div>${suggestions.map(s => `
        <div class="kv">
          <span class="kv-label">${s.category}</span>
          <span class="kv-value">${s.value} <span class="badge badge-mitigated">${Math.round(s.confidence * 100)}%</span></span>
        </div>
      `).join("")}` : ""}
      ${history.labels.length > 1 ? `<div class="section-sub">Label History</div>${history.labels.map(l => `<div class="kv"><span class="kv-label">${l.timestamp}</span><span class="kv-value">${l.expected_outcome}</span></div>`).join("")}` : ""}
      <div class="action-row" style="margin-top:12px">
        ${v.replayability === "requires_human_label" ? `<button class="btn btn-sm btn-amber" onclick="openAddLabelForm('${v.id}')">Add Label</button>` : ""}
        ${suggestions.length ? `<button class="btn btn-sm btn-outline" onclick="openSuggestLabelReview('${v.id}')">Review Suggested</button>` : ""}
      </div>
    `)}
    ${renderSection("Next Action", `
      <div class="action-row" id="vr-actions-${v.id}">
        ${v.replayability === "requires_human_label" ? `<button class="btn btn-sm btn-amber" onclick="openAddLabelForm('${v.id}')">Add Label</button>` : ""}
        ${v.replayability === "requires_sandbox" ? `<button class="btn btn-sm btn-amber" onclick="nav('systems')">Configure Sandbox</button>` : ""}
        ${v.replayability === "replayable" ? `<button class="btn btn-sm" data-action="replay" onclick="runVRReplay('${v.id}')">Replay</button>` : ""}
        ${v.replayability === "evidence_only" ? `<button class="btn btn-sm btn-outline" disabled title="Evidence-only: cannot replay">Evidence only</button>` : ""}
        ${v.replayability === "missing_context" ? `<button class="btn btn-sm btn-outline" onclick="openMissingContextHelp('${v.id}')">Resolve Missing Context</button>` : ""}
        <button class="btn btn-sm btn-green" data-action="mutation" onclick="runVRMutation('${v.id}')">Verify Fix</button>
        <button class="btn btn-sm btn-purple" data-action="issue_proof" onclick="issueVRProof('${v.id}')">Issue Proof</button>
        <button class="btn btn-sm btn-outline" data-action="promote_to_scenario" onclick="promoteVRToScenario('${v.id}')">Promote to Scenario</button>
      </div>
      <div id="vr-eligibility-${v.id}" style="margin-top:8px;font-size:11px;color:var(--muted)"></div>
    `)}
  `;
  // Load eligibility server-side for primary actions.
  loadVREligibility(v.id);
}

async function loadVREligibility(vrId) {
  try {
    const actions = ["replay", "mutation", "issue_proof", "promote_to_scenario"];
    const results = await Promise.all(actions.map(a => apiGet(`/v1/verification-records/${vrId}/eligibility/${a}`)));
    const box = q(`#vr-eligibility-${vrId}`);
    if (!box) return;
    const reasons = results.filter(r => !r.eligible && r.reason).map(r => `<span class="badge badge-planned">${r.action}</span> ${esc(r.reason)}`).join(" ");
    box.innerHTML = reasons ? `<div class="section-sub">Blocked actions.</div>${reasons}` : "All actions eligible";
    // Disable ineligible buttons and show reason in title.
    for (const r of results) {
      const btn = q(`#vr-actions-${vrId} [data-action="${r.action}"]`);
      if (btn) {
        if (r.eligible) {
          btn.disabled = false;
        } else {
          btn.disabled = true;
          btn.title = r.reason + (r.next_action ? " — Next: " + r.next_action : "");
        }
      }
    }
  } catch (e) {
    // ignore
  }
}

function openMissingContextHelp(vrId) {
  renderDrawer("Resolve Missing Context", `
    <p style="font-size:12px;color:var(--muted)">Missing context means the record lacks enough cassette or system data to replay.</p>
    <div class="section-title">Common fixes</div>
    <ul style="font-size:12px;color:var(--muted);margin-left:16px">
      <li>Capture all API/tool responses with the SDK.</li>
      <li>Include source-system record reference.</li>
      <li>For manual submissions, attach evidence summary.</li>
    </ul>
  `);
}

function openAddLabelForm(vrId) {
  const body = `
    <div class="np-form">
      <div class="np-field"><label>Expected Outcome</label><input id="label-outcome" placeholder="e.g. APPROVE"></div>
      <div class="np-field"><label>Reviewer</label><input id="label-reviewer" placeholder="e.g. QA Lead"></div>
      <div class="np-field"><label>Role</label><input id="label-role" placeholder="e.g. QA"></div>
      <div class="np-field"><label>Reason</label><textarea id="label-reason">Policy requires this outcome for the recorded scenario.</textarea></div>
    </div>
  `;
  const actions = `<button class="btn" onclick="submitLabel('${vrId}')">Add Label</button>`;
  renderDrawer("Add Human Label", body, actions);
}

async function submitLabel(vrId) {
  try {
    await apiPostForm("/v1/verification-records/" + vrId + "/label", {
      expected_outcome: q("#label-outcome").value,
      reviewer: q("#label-reviewer").value,
      role: q("#label-role").value,
      reason: q("#label-reason").value,
    });
    notify("Label added", "success");
    closeDrawer();
    R();
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

function openSuggestLabelReview(vrId) {
  renderDrawer("Review Suggested Labels", `
    <div id="suggest-review-body" style="font-size:12px;color:var(--muted)">Loading...</div>
  `);
  apiPost("/v1/verification-records/" + vrId + "/label-suggest").then(r => {
    const body = q("#suggest-review-body");
    body.innerHTML = `
      <div class="section-title">Suggested Labels</div>
      ${r.suggested_labels.map(s => `
        <div class="kv" style="margin:6px 0;padding:8px;background:var(--surface-2);border-radius:6px">
          <span class="kv-label">${s.category}</span>
          <span class="kv-value">${s.value} <span class="badge badge-mitigated">${Math.round(s.confidence * 100)}%</span></span>
          <div style="font-size:11px;color:var(--dim);margin-top:4px">${s.reasoning}</div>
          <div class="action-row" style="margin-top:8px">
            <button class="btn btn-sm btn-green" onclick="approveSuggestedLabel('${vrId}', '${s.value}', '${s.category}')">Approve</button>
            <button class="btn btn-sm btn-outline" onclick="rejectSuggestedLabel('${vrId}', '${s.value}')">Reject</button>
          </div>
        </div>
      `).join("")}
    `;
  }).catch(e => {
    q("#suggest-review-body").innerHTML = `<p class="error-state">${e.message}</p>`;
  });
}

async function approveSuggestedLabel(vrId, value, category) {
  try {
    await apiPostForm("/v1/verification-records/" + vrId + "/label", {
      expected_outcome: value,
      reviewer: "Platform User",
      role: "QA",
      reason: "Approved suggested " + category + " label",
    });
    notify("Approved label", "success");
    closeDrawer();
    R();
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function rejectSuggestedLabel(vrId, value) {
  try {
    await apiPost("/v1/verification-records/" + vrId + "/label-reject", {value});
    notify("Rejected suggestion", "success");
    openSuggestLabelReview(vrId);
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function openVRPreflight(vrId) {
  try {
    const p = await apiGet("/v1/verification-records/" + vrId + "/replay-preflight");
    const blocks = p.blocking_factors.map(f => renderWorkflowStep(f.component, "fail", f.description, `<span class="badge badge-red">${f.severity}</span>`)).join("");
    const warns = p.warnings.map(w => renderWorkflowStep(w.component, "warn", w.description, `<span class="badge badge-mitigated">${w.severity}</span>`)).join("");
    renderDrawer("Replay Preflight", `
      <div style="margin:8px 0">${renderStatusBadge(p.preflight_status.toLowerCase(), p.preflight_status)}</div>
      <div class="section-title">Replayability</div>
      <p style="font-size:12px;color:var(--muted)">${p.replayability_state.replace(/_/g, " ")} — score ${Math.round((p.replayability_score || 0) * 100)}%</p>
      ${blocks ? `<div class="section-title">Blocking Factors</div>${blocks}` : ""}
      ${warns ? `<div class="section-title">Warnings</div>${warns}` : ""}
      ${p.can_proceed ? `<button class="btn" onclick="promoteVR('${vrId}')">Promote to Incident</button>` : `<button class="btn" disabled>Cannot proceed</button>`}
    `);
  } catch (e) {
    notify("Preflight failed: " + e.message, "error");
  }
}

async function promoteVR(vrId) {
  try {
    const r = await apiPost("/v1/verification-records/" + vrId + "/promote-to-incident");
    notify("Promoted to " + r.incident_id, "success");
    openIncidentDetail(r.incident_id);
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function runVRReplay(vrId) {
  try {
    const r = await apiPost("/v1/verification-records/" + vrId + "/replay-runs");
    notify("Replay run " + r.status, r.status === "replayed" ? "success" : "error");
    openVRDetail(vrId);
  } catch (e) {
    notify("Replay failed: " + e.message, "error");
  }
}

async function runVRMutation(vrId) {
  try {
    const r = await apiPost("/v1/verification-records/" + vrId + "/mutation-tests", {
      fix_config: {threshold: 620},
      expected_correct_behavior: "APPROVE",
    });
    notify("Mutation test " + r.verdict, r.verdict === "verified" ? "success" : "error");
    openVRDetail(vrId);
  } catch (e) {
    notify("Mutation failed: " + e.message, "error");
  }
}

async function issueVRProof(vrId) {
  try {
    const r = await apiPost("/v1/verification-records/" + vrId + "/proof-of-mitigation");
    notify("Proof issued: " + r.id, "success");
    openVRDetail(vrId);
  } catch (e) {
    notify("Proof failed: " + e.message, "error");
  }
}

async function promoteVRToScenario(vrId) {
  try {
    const r = await apiPost("/v1/scenarios", {vr_id: vrId});
    notify("Promoted to scenario " + r.id, "success");
    S.selectedScenario = r.id;
    nav("scenario-detail");
  } catch (e) {
    notify("Promotion failed: " + e.message, "error");
  }
}

async function seedDemo() {
  try {
    const r = await apiPost("/v1/platform/seed-demo?depth=full");
    notify(`Seeded ${r.created_verification_records} records, ${r.created_incidents} incidents, ${r.created_proofs} proofs`, "success");
    R();
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

// --- INCIDENTS ---

function renderIncidents(c, ix) {
  if (!ix.length) {
    c.innerHTML = renderEmptyState("No Incidents", "Promote a Verification Record or seed demo data.", `<button class="btn" onclick="seedDemo()">Seed Demo Data</button>`);
    return;
  }
  const counts = {
    all: ix.length,
    ingested: ix.filter(i => i.status === "ingested").length,
    replayed: ix.filter(i => i.status === "replayed").length,
    mitigated: ix.filter(i => i.status === "mitigated").length,
    certified: ix.filter(i => i.status === "certified").length,
  };
  const pills = Object.keys(counts).map(k => ({key: k, label: k.replace(/^./, x => x.toUpperCase()) + " (" + counts[k] + ")", active: false, onClick: `filterIncidents('${k}')`}));
  c.innerHTML = `
    ${renderFilterPills(pills)}
    <table>
      <thead><tr><th>ID</th><th>Status</th><th>R</th><th>F</th><th>C</th><th>Actions</th></tr></thead>
      <tbody>${ix.map(i => `
        <tr class="inc-row" data-status="${esc(i.status)}">
          <td>${badgeDemo()} <span class="link" onclick="openIncidentDetail('${i.incident_id}')">${i.incident_id}</span></td>
          <td>${statusBadge(i.status)}</td>
          <td>${i.replay_result && Object.keys(i.replay_result).length ? "✓" : "—"}</td>
          <td>${i.mutation_result && Object.keys(i.mutation_result).length ? "✓" : "—"}</td>
          <td>${i.certificate && Object.keys(i.certificate).length ? "✓" : "—"}</td>
          <td class="action-row">
            ${!i.replay_result ? `<button class="btn btn-sm" onclick="runIncidentReplay('${i.incident_id}')">Replay</button>` : ""}
            ${i.replay_result && !i.mutation_result ? `<button class="btn btn-sm btn-amber" onclick="runIncidentVerify('${i.incident_id}')">Verify Fix</button>` : ""}
            ${i.mutation_result && !i.certificate ? `<button class="btn btn-sm btn-green" onclick="runIncidentCertify('${i.incident_id}')">Issue Proof</button>` : ""}
            <button class="btn btn-sm btn-outline" onclick="openIncidentDetail('${i.incident_id}')">Investigate</button>
          </td>
        </tr>
      `).join("")}
      </tbody>
    </table>
  `;
  window._incFilter = "all";
}

function filterIncidents(s) {
  window._incFilter = s;
  qa(".inc-row").forEach(r => r.classList.toggle("hidden", s !== "all" && r.dataset.status !== s));
  qa(".filter-pill").forEach(p => p.classList.toggle("active", p.dataset.filter === s));
}

function openIncidentDetail(id) {
  S.selectedIncident = id;
  nav("incident-detail");
}

async function renderIncidentDetail(c, i, wf) {
  const sourceVr = await apiGet("/v1/verification-records").then(vrs => vrs.find(v => v.promoted_to_incident === i.incident_id) || null).catch(() => null);
  const cert = i.certificate || {};
  let sigValid = null;
  if (cert.certificate_id) {
    sigValid = await apiGet(`/v1/incidents/${i.incident_id}/certificates/${cert.certificate_id}/verify`).then(r => r.signature_valid).catch(() => null);
  }
  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('incidents')">← Back to Incidents</button>
    ${badgeDemo()}
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      ${statusBadge(i.status)}
      <span style="font-size:13px;color:var(--muted)">ID: ${i.incident_id}</span>
    </div>
    ${renderSection("Proof Loop Workflow", wf.steps.map(s => renderWorkflowStep(s.label, s.state, s.detail, s.action ? `<button class="btn btn-sm" onclick="wfAction('${i.incident_id}', '${s.label}')">${s.action}</button>` : "")).join(""))}
    ${sourceVr ? renderSection("Source Verification Record", `
      <div class="action-row">
        <button class="btn btn-sm btn-outline" onclick="openVRDetail('${sourceVr.id}')">View ${sourceVr.id}</button>
        ${statusBadge(sourceVr.replayability)}
      </div>
    `) : ""}
    ${renderSection("Evidence", `
      ${renderKV("Root Hash", (i.snapshot_summary?.root_hash || "—").substring(0, 30) + "...")}
      ${renderKV("Elements", i.snapshot_summary?.element_count || "—")}
      ${renderKV("Integrity", i.snapshot_summary?.integrity || "—")}
    `)}
    ${i.replay_result ? renderSection("Replay Result", `
      ${renderKV("Decision", i.replay_result.decision || "—")}
      ${renderKV("Replay Status", i.replay_result.replay_status || "—")}
    `) : ""}
    ${i.mutation_result ? renderSection("Fix Verification", `
      ${renderKV("Original", i.mutation_result.original_decision)}
      ${renderKV("Mutated", `<span style="color:${i.mutation_result.mitigated ? 'var(--green)' : 'var(--red)'}">${i.mutation_result.mutated_decision}</span>`)}
      ${renderKV("Mitigated", i.mutation_result.mitigated ? "✓ Yes" : "✗ No")}
    `) : ""}
    ${cert.certificate_id ? renderSection("Proof", `
      <div class="proof-bundle">
        <h3>${cert.certificate_id}</h3>
        ${renderKV("Algorithm", cert.signing_algorithm || "—")}
        ${renderKV("Signature Valid", sigValid === true ? "✓ Yes" : sigValid === false ? "✗ No" : "Unknown")}
        ${renderKV("Claim Scope", "Verified fix for this tested scenario under recorded conditions. Does not certify general AI safety.")}
        ${renderKV("Limitations", cert.known_limitations || "—")}
        <div class="action-row" style="margin-top:12px">
          <a href="/v1/incidents/${i.incident_id}/certificates/${cert.certificate_id}/download" class="btn btn-sm btn-outline" style="text-decoration:none">Download JSON</a>
          <a href="/v1/incidents/${i.incident_id}/certificates/${cert.certificate_id}/export-pdf" class="btn btn-sm btn-outline" style="text-decoration:none">Download PDF</a>
          <button class="btn btn-sm btn-outline" onclick="verifyIncidentCert('${i.incident_id}')">Verify Signature</button>
        </div>
      </div>
    `) : ""}
    <div class="action-row" style="margin-top:16px">
      ${!i.replay_result ? `<button class="btn" onclick="runIncidentReplay('${i.incident_id}')">Run Replay</button>` : ""}
      ${i.replay_result && !i.mutation_result ? `<button class="btn btn-amber" onclick="runIncidentVerify('${i.incident_id}')">Verify Fix</button>` : ""}
      ${i.mutation_result && !cert.certificate_id ? `<button class="btn btn-green" onclick="runIncidentCertify('${i.incident_id}')">Issue Proof</button>` : ""}
      ${cert.certificate_id ? `<button class="btn btn-sm btn-outline" onclick="nav('scenarios')">Promote to Scenario</button>` : ""}
    </div>
  `;
}

function wfAction(incidentId, label) {
  if (label.includes("Replay")) runIncidentReplay(incidentId);
  else if (label.includes("Fix")) runIncidentVerify(incidentId);
  else if (label.includes("Proof")) runIncidentCertify(incidentId);
}

async function runIncidentReplay(id) {
  try {
    await apiPost("/v1/incidents/" + id + "/replay");
    notify("Replay completed", "success");
    openIncidentDetail(id);
  } catch (e) {
    notify("Replay failed: " + e.message, "error");
  }
}

async function runIncidentVerify(id) {
  try {
    await apiPost("/v1/incidents/" + id + "/mutation-tests", {fix_config: {threshold: 620}, expected_correct_behavior: "APPROVE"});
    notify("Fix verification completed", "success");
    openIncidentDetail(id);
  } catch (e) {
    notify("Fix verification failed: " + e.message, "error");
  }
}

async function runIncidentCertify(id) {
  try {
    await apiPost("/v1/incidents/" + id + "/certificates");
    notify("Proof issued", "success");
    openIncidentDetail(id);
  } catch (e) {
    notify("Proof issue failed: " + e.message, "error");
  }
}

async function verifyIncidentCert(id) {
  try {
    const i = await apiGet("/v1/incidents/" + id);
    const cert = i.certificate || {};
    if (!cert.certificate_id) throw new Error("No certificate");
    const v = await apiGet(`/v1/incidents/${id}/certificates/${cert.certificate_id}/verify`);
    notify(v.signature_valid ? "Signature valid ✓" : "Signature invalid ✗", v.signature_valid ? "success" : "error");
  } catch (e) {
    notify("Verification failed: " + e.message, "error");
  }
}

// --- PROOFS ---

function renderProofs(c, proofs) {
  if (!proofs.length) {
    c.innerHTML = renderEmptyState("No Proofs", "Issue a proof from an incident.", `<button class="btn" onclick="nav('incidents')">Go to Incidents</button>`);
    return;
  }
  c.innerHTML = `
    <div class="section-title">Issued Proofs</div>
    <div class="section-sub">Evidence packages with bounded claim scope and limitations.</div>
    <table>
      <thead><tr><th>Proof</th><th>Incident</th><th>Source System</th><th>Score</th><th>Claim Scope</th><th>Actions</th></tr></thead>
      <tbody>${proofs.map(p => `
        <tr>
          <td>${badgeDemo()} <span class="link" onclick="openProofDetail('${p.proof_id}')">${p.proof_id}</span></td>
          <td><span class="link" onclick="openIncidentDetail('${p.incident_id}')">${p.incident_id}</span></td>
          <td>${esc(p.source_system_id || "—")}</td>
          <td><span style="font-weight:800;color:${(p.replayability_score || 0) >= 0.8 ? 'var(--green)' : 'var(--amber)'}">${Math.round((p.replayability_score || 0) * 100)}%</span></td>
          <td style="font-size:11px">Bounded to tested scenario</td>
          <td class="action-row">
            <button class="btn btn-sm btn-outline" onclick="openProofDetail('${p.proof_id}')">View</button>
            <a href="/v1/incidents/${p.incident_id}/certificates/${p.proof_id}/download" class="btn btn-sm btn-outline" style="text-decoration:none">JSON</a>
            <a href="/v1/incidents/${p.incident_id}/certificates/${p.proof_id}/export-pdf" class="btn btn-sm btn-outline" style="text-decoration:none">PDF</a>
          </td>
        </tr>
      `).join("")}
      </tbody>
    </table>
  `;
}

function openProofDetail(proofId) {
  S.selectedProof = proofId;
  nav("proof-detail");
}

async function renderProofDetail(c, p) {
  const sig = await apiGet(`/v1/incidents/${p.incident_id}/certificates/${p.proof_id}/verify`).then(r => r.signature_valid).catch(() => null);
  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('proofs')">← Back to Proofs</button>
    ${badgeDemo()}
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      ${statusBadge("certified")}
      <span style="font-size:13px;color:var(--muted)">ID: ${p.proof_id}</span>
    </div>
    <div class="proof-bundle">
      <h3>${p.proof_id}</h3>
      ${renderKV("Source Incident", `<span class="link" onclick="openIncidentDetail('${p.incident_id}')">${p.incident_id}</span>`)}
      ${renderKV("Source Verification Record", p.verification_record_id ? `<span class="link" onclick="openVRDetail('${p.verification_record_id}')">${p.verification_record_id}</span>` : "—")}
      ${renderKV("Source System", p.source_system_id || "—")}
      ${renderKV("Label", p.label_id ? `<span class="link" onclick="openVRDetail('${p.verification_record_id}')">View label</span>` : "—")}
      ${renderKV("Replayability Score", `<span style="font-weight:800;color:${(p.replayability_score || 0) >= 0.8 ? 'var(--green)' : 'var(--amber)'}">${Math.round((p.replayability_score || 0) * 100)}%</span>`)}
      ${renderKV("Deterministic Coverage", (p.replayability_score || 0) >= 0.8 ? "High" : (p.replayability_score || 0) >= 0.5 ? "Partial" : "Evidence-only")}
      ${renderKV("Non-Deterministic Flags", (p.non_deterministic_flags || []).length ? (p.non_deterministic_flags || []).map(f => `<span class="badge badge-mitigated">${f.component}</span>`).join(" ") : "None")}
      ${renderKV("Original Decision", p.original_decision || "—")}
      ${renderKV("Verified Decision", p.mutated_decision || "—")}
      ${renderKV("Claim Scope", p.claim_scope)}
      ${renderKV("Limitations", p.known_limitations || "None documented")}
      ${renderKV("Signature Status", sig === true ? "✓ Valid" : sig === false ? "✗ Invalid" : "Unknown")}
      ${renderKV("Verification Instructions", "Verify the JSON signature using Notary's public key or via the API endpoint.")}
      <div class="action-row" style="margin-top:12px">
        <a href="/v1/incidents/${p.incident_id}/certificates/${p.proof_id}/download" class="btn btn-sm btn-outline" style="text-decoration:none">Download JSON</a>
        <a href="/v1/incidents/${p.incident_id}/certificates/${p.proof_id}/export-pdf" class="btn btn-sm btn-outline" style="text-decoration:none">Download PDF</a>
        <button class="btn btn-sm btn-outline" onclick="verifyProofSig('${p.incident_id}', '${p.proof_id}')">Verify Signature</button>
      </div>
    </div>
  `;
}

async function verifyProofSig(incidentId, proofId) {
  try {
    const v = await apiGet(`/v1/incidents/${incidentId}/certificates/${proofId}/verify`);
    notify(v.signature_valid ? "Signature valid ✓" : "Signature invalid ✗", v.signature_valid ? "success" : "error");
  } catch (e) {
    notify("Verification failed: " + e.message, "error");
  }
}

// --- SYSTEMS ---

function renderSystems(c, systems) {
  if (!systems.length) {
    c.innerHTML = renderEmptyState("No Systems", "Configure systems in Settings or seed demo data.");
    return;
  }
  const typeGroups = {};
  systems.forEach(s => {
    const t = s.type || "source_system";
    typeGroups[t] = typeGroups[t] || [];
    typeGroups[t].push(s);
  });
  c.innerHTML = `
    <div class="section-title">Systems Registry</div>
    <div class="section-sub">Operational registry for your AI decision environment.</div>
    ${Object.entries(typeGroups).map(([type, items]) => `
      <div class="section-title" style="text-transform:capitalize">${type.replace(/_/g, " ")}</div>
      ${items.map(s => `
        <div class="int-card" onclick="openSystemDetail('${s.id}')">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <h4>${s.name}</h4>
              <p>${s.capability || "—"}</p>
            </div>
            <div class="action-row">
              <span class="status-dot status-${s.status === "connected" ? "connected" : s.status === "planned" ? "planned" : "disconnected"}"></span>
              <span class="badge badge-${s.status === "connected" ? "built" : s.status === "planned" ? "planned" : "red"}">${s.status}</span>
            </div>
          </div>
          <div class="action-row" style="margin-top:12px">
            <button class="btn btn-sm btn-outline" onclick="event.stopPropagation();testSystemConnection('${s.id}')">Test Connection</button>
            <button class="btn btn-sm btn-outline" onclick="event.stopPropagation();openSystemDetail('${s.id}')">Detail</button>
          </div>
        </div>
      `).join("")}
    `).join("")}
  `;
}

function openSystemDetail(id) {
  S.selectedSystem = id;
  nav("system-detail");
}

async function renderSystemDetail(c, s, vrs) {
  const linked = (vrs || []).filter(v => v.source_system_id === s.id || s.linked_vrs.includes(v.id));
  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('systems')">← Back to Systems</button>
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      <span class="status-dot status-${s.status === "connected" ? "connected" : s.status === "planned" ? "planned" : "disconnected"}"></span>
      ${statusBadge(s.status)}
      <span style="font-size:13px;color:var(--muted)">ID: ${s.id}</span>
    </div>
    ${renderSection("Summary", `
      ${renderKV("Type", s.type)}
      ${renderKV("Kind", s.kind)}
      ${renderKV("Capability", s.capability || "—")}
      ${renderKV("Auth Status", s.auth_status)}
      ${renderKV("Last Checked", s.last_checked || "Never")}
      ${renderKV("Fallback", s.fallback || "—")}
    `)}
    ${renderSection("Replay / Sandbox", `
      ${renderKV("Sandbox Supported", s.sandbox_supported ? "Yes" : "No")}
      ${renderKV("Replay Modes", s.sandbox_replay_modes.join(", ") || "—")}
      ${renderKV("Supported Agents", s.supported_agents.join(", ") || "—")}
    `)}
    ${renderSection("Limitations", (s.limitations || []).length ? `<ul style="font-size:12px;color:var(--muted);margin-left:16px">${s.limitations.map(l => `<li>${esc(l)}</li>`).join("")}</ul>` : "No documented limitations")}
    ${renderSection("Linked Verification Records", linked.length ? `
      <table>
        <thead><tr><th>VR</th><th>Replayability</th></tr></thead>
        <tbody>${linked.map(v => `<tr><td><span class="link" onclick="openVRDetail('${v.id}')">${v.id}</span></td><td>${statusBadge(v.replayability)}</td></tr>`).join("")}</tbody>
      </table>
    ` : "No linked records")}
    <div class="action-row" style="margin-top:16px">
      <button class="btn" onclick="testSystemConnection('${s.id}')">Test Connection</button>
      ${s.sandbox_supported ? `<button class="btn btn-outline" onclick="notify('Sandbox configuration is demo-only')">Configure Sandbox</button>` : renderDisabledAction("Configure Sandbox", "Sandbox not supported for this system")}
    </div>
  `;
}

async function testSystemConnection(id) {
  try {
    const r = await apiPost("/v1/platform/org/systems/" + id + "/test");
    notify(r.message, r.status === "healthy" ? "success" : "error");
    R();
  } catch (e) {
    notify("Test failed: " + e.message, "error");
  }
}

// --- SCENARIOS ---

function renderScenarios(c, scenarios, candidates) {
  c.innerHTML = `
    <div class="section-title">Scenario Library</div>
    <div class="section-sub">Promote verified incidents to reusable scenarios, run them against agent versions, and use them in readiness policies.</div>
    ${renderSection("Active Scenarios", scenarios.length ? scenarios.map(s => scenarioCard(s)).join("") : "No scenarios in the library yet")}
    ${renderSection("Scenario Candidates", candidates.length ? candidates.filter(sc => sc.state === "candidate").map(sc => candidateCard(sc)).join("") : "No candidates ready")}
  `;
}

function scenarioCard(sc) {
  return `
    <div class="int-card">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <h4>${esc(sc.business_title)}</h4>
          <p style="font-size:12px;color:var(--muted)">Expected outcome: ${esc(sc.expected_outcome)} · Source: ${sc.source_vr_id}</p>
        </div>
        <span class="badge badge-${sc.state === "active" ? "built" : "planned"}">${sc.state}</span>
      </div>
      <div style="font-size:12px;color:var(--muted);margin-top:8px">
        Replayability: ${statusBadge(sc.replayability)} ${Math.round((sc.replayability_score || 0) * 100)}% · Sandbox: ${sc.required_sandbox_id || "—"} · Last run: ${sc.last_run_status || "not_started"}
      </div>
      <div class="action-row" style="margin-top:12px">
        <button class="btn btn-sm" onclick="runScenarioSet(['${sc.id}'])">Run This Scenario</button>
        <button class="btn btn-sm btn-outline" onclick="openScenarioDetail('${sc.id}')">Detail</button>
      </div>
    </div>`;
}

function candidateCard(sc) {
  return `
    <div class="int-card">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <h4>${esc(sc.business_title)}</h4>
          <p style="font-size:12px;color:var(--muted)">Source: ${sc.source_vr_id}</p>
        </div>
        ${statusBadge(sc.state)}
      </div>
      <div style="font-size:12px;color:var(--muted);margin-top:8px">
        Replayability: ${statusBadge(sc.replayability)} ${Math.round((sc.replayability_score || 0) * 100)}%
      </div>
      <div class="action-row" style="margin-top:12px">
        <button class="btn btn-sm btn-green" onclick="promoteCandidate('${sc.id}')">Promote to Scenario</button>
        <button class="btn btn-sm btn-outline" onclick="openVRDetail('${sc.source_vr_id}')">View Source V.R.</button>
      </div>
    </div>`;
}

function openScenarioDetail(id) {
  S.selectedScenario = id;
  nav("scenario-detail");
}

async function renderScenarioDetail(c, s, runs) {
  const sourceRuns = runs.filter(r => r.scenario_ids.includes(s.id));
  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('scenarios')">← Back to Scenarios</button>
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      <span class="badge badge-${s.state === "active" ? "built" : "planned"}">${s.state}</span>
      <span style="font-size:13px;color:var(--muted)">ID: ${s.id}</span>
    </div>
    ${renderSection("Summary", `
      ${renderKV("Business Title", s.business_title)}
      ${renderKV("Source V.R.", `<span class="link" onclick="openVRDetail('${s.source_vr_id}')">${s.source_vr_id}</span>`)}
      ${renderKV("Expected Outcome", s.expected_outcome)}
      ${renderKV("Replayability", statusBadge(s.replayability))}
      ${renderKV("Last Run Status", s.last_run_status || "not_started")}
    `)}
    ${renderSection("Run History", sourceRuns.length ? `
      <table>
        <thead><tr><th>Run</th><th>Agent Version</th><th>Status</th><th>Result</th></tr></thead>
        <tbody>${sourceRuns.map(r => `
          <tr>
            <td><span class="link" onclick="openScenarioRunDetail('${r.id}')">${r.id}</span></td>
            <td>${esc(r.agent_version)}</td>
            <td>${statusBadge(r.status)}</td>
            <td>${JSON.stringify(r.summary)}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    ` : "No runs yet")}
    <div class="action-row" style="margin-top:16px">
      <button class="btn" onclick="runScenarioSet(['${s.id}'])">Run This Scenario</button>
      <button class="btn btn-outline" onclick="createReadinessPolicyForScenario('${s.id}')">Add to Readiness Policy</button>
      ${s.state === "active" ? `<button class="btn btn-sm btn-outline" onclick="retireScenario('${s.id}')">Retire</button>` : `<button class="btn btn-sm btn-outline" onclick="reactivateScenario('${s.id}')">Reactivate</button>`}
    </div>
  `;
}

async function openScenarioRunDetail(runId) {
  try {
    const run = await apiGet("/v1/scenario-runs/" + runId);
    const body = `
      <div class="section-title">Results</div>
      ${renderTable(["Scenario", "Expected", "Actual", "Status", "Reason"], run.results.map(r => [
        r.scenario_id,
        esc(r.expected_decision),
        esc(r.actual_decision),
        statusBadge(r.status),
        esc(r.reason || "—"),
      ]))}
    `;
    renderDrawer("Scenario Run " + runId, body);
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function promoteCandidate(candidateId) {
  try {
    const r = await apiPost("/v1/scenario-candidates/" + candidateId + "/promote");
    notify("Promoted to scenario " + r.id, "success");
    nav("scenarios");
  } catch (e) {
    notify("Promotion failed: " + e.message, "error");
  }
}

async function runScenarioSet(scenarioIds) {
  try {
    const r = await apiPost("/v1/scenario-runs", {scenario_ids: scenarioIds, agent_version: S.agentVersion});
    notify(`Scenario run ${r.status}: ${r.summary.passed} passed, ${r.summary.failed} failed, ${r.summary.errored} errored`, "success");
    nav("scenarios");
  } catch (e) {
    notify("Scenario run failed: " + e.message, "error");
  }
}

async function retireScenario(id) {
  try {
    await apiPatch("/v1/scenarios/" + id, {state: "retired"});
    notify("Scenario retired", "success");
    R();
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function reactivateScenario(id) {
  try {
    await apiPatch("/v1/scenarios/" + id, {state: "active"});
    notify("Scenario reactivated", "success");
    R();
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

// --- READINESS ---

function renderReadiness(c, policies, checks) {
  c.innerHTML = `
    <div class="section-title">Readiness Policies</div>
    <div class="section-sub">Define which Scenarios must pass before an agent version can ship.</div>
    ${policies.length ? policies.map(p => `
      <div class="int-card">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <h4>${esc(p.name)} <span class="badge badge-planned">v${p.version}</span></h4>
            <p style="font-size:12px;color:var(--muted)">Required scenarios: ${p.required_scenario_ids.join(", ") || "—"}</p>
          </div>
          <span class="badge badge-${p.enabled ? "built" : "planned"}">${p.enabled ? "enabled" : "disabled"}</span>
        </div>
        <div class="action-row" style="margin-top:12px">
          <button class="btn btn-sm" onclick="runReadinessCheck('${p.id}', S.agentVersion)">Run Check</button>
          <button class="btn btn-sm btn-green" onclick="triggerReleaseGate('${p.id}', S.agentVersion)">Release Gate</button>
          <button class="btn btn-sm btn-outline" onclick="togglePolicy('${p.id}', ${!p.enabled})">${p.enabled ? "Disable" : "Enable"}</button>
        </div>
      </div>
    `).join("") : `<p style="font-size:12px;color:var(--muted)">No readiness policies. Create one from the Scenario detail view or below.</p>`}
    <div class="action-row" style="margin-top:16px">
      <button class="btn" onclick="openCreatePolicyForm()">Create Policy</button>
    </div>
    ${renderSection("Readiness Checks", checks.length ? `
      <table>
        <thead><tr><th>Check</th><th>Policy</th><th>Agent Version</th><th>Verdict</th><th>Actions</th></tr></thead>
        <tbody>${checks.map(ch => `
          <tr>
            <td><span class="link" onclick="openReadinessDetail('${ch.id}')">${ch.id}</span></td>
            <td>${esc(ch.policy_id)}</td>
            <td>${esc(ch.agent_version)}</td>
            <td>${statusBadge(ch.verdict)}</td>
            <td class="action-row">
              <button class="btn btn-sm btn-outline" onclick="openReadinessDetail('${ch.id}')">Detail</button>
            </td>
          </tr>
        `).join("")}</tbody>
      </table>
    ` : "No readiness checks yet")}
  `;
}

function openCreatePolicyForm() {
  const body = `
    <div class="np-form">
      <div class="np-field"><label>Policy Name</label><input id="policy-name" value="Lending Release Gate"></div>
      <div class="np-field"><label>Required Scenario IDs (comma-separated)</label><input id="policy-scenarios" placeholder="sc-abc123, sc-def456"></div>
    </div>
  `;
  const actions = `<button class="btn" onclick="submitPolicyForm()">Create Policy</button>`;
  renderDrawer("Create Readiness Policy", body, actions);
}

async function submitPolicyForm() {
  try {
    const ids = q("#policy-scenarios").value.split(",").map(s => s.trim()).filter(Boolean);
    const r = await apiPost("/v1/readiness-policies", {name: q("#policy-name").value, required_scenario_ids: ids});
    notify("Created policy " + r.id, "success");
    closeDrawer();
    nav("readiness");
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function createReadinessPolicyForScenario(scenarioId) {
  try {
    const r = await apiPost("/v1/readiness-policies", {name: "Policy for " + scenarioId, required_scenario_ids: [scenarioId]});
    notify("Created policy " + r.id, "success");
    nav("readiness");
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function togglePolicy(policyId, enabled) {
  try {
    await apiPatch("/v1/readiness-policies/" + policyId, {enabled});
    notify("Policy " + (enabled ? "enabled" : "disabled"), "success");
    R();
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function runReadinessCheck(policyId, agentVersion) {
  try {
    const r = await apiPost("/v1/readiness-checks", {policy_id: policyId, agent_version: agentVersion});
    notify("Readiness check " + r.verdict, r.verdict === "passed" ? "success" : "error");
    S.selectedReadinessCheck = r.id;
    nav("readiness-detail");
  } catch (e) {
    notify("Readiness check failed: " + e.message, "error");
  }
}

async function triggerReleaseGate(policyId, agentVersion) {
  try {
    const r = await apiPost("/v1/release-gate/checks", {policy_id: policyId, agent_version: agentVersion});
    notify("Release gate " + r.status, r.status === "pass" ? "success" : "error");
    S.selectedReleaseGate = r.id;
    nav("release-gate-detail");
  } catch (e) {
    notify("Release gate failed: " + e.message, "error");
  }
}

function openReadinessDetail(id) {
  S.selectedReadinessCheck = id;
  nav("readiness-detail");
}

async function renderReadinessDetail(c, check) {
  const run = await apiGet("/v1/scenario-runs/" + check.scenario_run_id).catch(() => null);
  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('readiness')">← Back to Readiness</button>
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      ${statusBadge(check.verdict)}
      <span style="font-size:13px;color:var(--muted)">ID: ${check.id}</span>
    </div>
    ${renderSection("Summary", `
      ${renderKV("Policy", check.policy_id)}
      ${renderKV("Agent Version", check.agent_version)}
      ${renderKV("Scenario Run", check.scenario_run_id)}
      ${renderKV("Certificate", check.certificate_id || "—")}
    `)}
    ${run ? renderSection("Scenario Run Results", `
      ${renderTable(["Scenario", "Expected", "Actual", "Status"], run.results.map(r => [
        r.scenario_id,
        esc(r.expected_decision),
        esc(r.actual_decision),
        statusBadge(r.status),
      ]))}
    `) : ""}
    ${check.failing_scenarios.length ? renderSection("Failing Scenarios", `<div class="badge badge-red">${check.failing_scenarios.join(", ")}</div>`) : ""}
    ${check.errored_scenarios.length ? renderSection("Errored Scenarios", `<div class="badge badge-planned">${check.errored_scenarios.join(", ")}</div>`) : ""}
  `;
}

async function renderReleaseGateDetail(c, gate) {
  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('readiness')">← Back to Readiness</button>
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      ${statusBadge(gate.status)}
      <span style="font-size:13px;color:var(--muted)">ID: ${gate.id}</span>
    </div>
    ${renderSection("Machine-Readable Result", `
      ${renderKV("Status", gate.status)}
      ${renderKV("Readiness Check", gate.readiness_check_id || "—")}
      ${renderKV("Certificate", gate.certificate_id || "—")}
      ${renderKV("Error Code", gate.error_code || "—")}
      ${renderKV("Retry Guidance", gate.retry_guidance || "—")}
    `)}
    ${renderSection("CI/CD Command", `
      ${renderCodeBlock(gate.ci_cd_command)}
    `)}
    ${gate.failing_scenarios.length ? renderSection("Failing Scenarios", `<div class="badge badge-red">${gate.failing_scenarios.join(", ")}</div>`) : ""}
    ${gate.errored_scenarios.length ? renderSection("Errored Scenarios", `<div class="badge badge-planned">${gate.errored_scenarios.join(", ")}</div>`) : ""}
  `;
}

// --- GOVERNANCE ---

function renderGovernance(c, vrs) {
  const suggested = vrs.filter(v => v.suggested_labels && v.suggested_labels.length);
  const needLabel = vrs.filter(v => v.replayability === "requires_human_label" && !v.current_label_id);
  const approved = vrs.filter(v => v.current_label_id);
  c.innerHTML = `
    <div class="section-title">Governance</div>
    <div class="section-sub">Label provenance, review queue, claim scope, and audit.</div>
    ${renderSection("Label Review Queue", `
      <div class="queue-row">
        ${chip(suggested.length, "Suggested labels", "--accent", "verification-records")}
        ${chip(needLabel.length, "Need manual label", "--amber", "verification-records")}
        ${chip(approved.length, "Approved labels", "--green", "verification-records")}
      </div>
    `)}
    ${renderSection("Bulk Actions", `
      <div class="action-row">
        <button class="btn btn-sm" onclick="bulkApproveHighConfidence()">Bulk Approve High-Confidence</button>
      </div>
    `)}
    ${renderSection("Claim Scope / Limitations", `
      <p style="font-size:12px;color:var(--muted)">Notary proofs are bounded to the tested scenario under recorded conditions. They do not certify general AI safety.</p>
      <div class="section-sub">Planned</div>
      <ul style="font-size:12px;color:var(--muted);margin-left:16px">
        <li>Regulatory mappings</li>
        <li>Retention and legal hold</li>
        <li>GRC push status</li>
        <li>Full audit log</li>
      </ul>
    `)}
  `;
}

async function bulkApproveHighConfidence() {
  try {
    const r = await apiPost("/v1/verification-records/bulk-label-approve", {filter: {suggested_confidence_min: 0.7, suggested_confidence_max: 1.0}, approval_reason: "Bulk approved from Governance"});
    notify(`Bulk approved ${r.approved_count} labels`, "success");
    R();
  } catch (e) {
    notify("Bulk approve failed: " + e.message, "error");
  }
}

// --- SETTINGS ---

async function renderSettings(c) {
  c.innerHTML = `
    <div class="section-title">Settings</div>
    <div class="section-sub">Organization, auth, API keys, and integrations.</div>
    ${renderSection("Authentication", `
      <div class="np-form">
        <div class="np-field">
          <label>API Token for /v1 calls</label>
          <input type="text" id="settings-token" value="${esc(S.token)}" placeholder="ntry-...">
        </div>
        <button class="btn btn-sm" onclick="saveSettingsToken()">Save Token</button>
      </div>
      <p style="font-size:12px;color:var(--muted);margin-top:8px">/health, /app, and /cc are public. /v1 endpoints require this token.</p>
    `)}
    ${renderSection("API Keys", `
      <div class="action-row">
        <button class="btn btn-sm" onclick="createApiKey()">Create API Key</button>
        <button class="btn btn-sm btn-outline" onclick="loadApiKeys()">Refresh</button>
      </div>
      <div id="api-keys-list" style="margin-top:12px">${sk(40)}</div>
    `)}
    ${renderSection("Organization", `
      ${renderKV("Name", "Acme Assurance Demo")}
      ${renderKV("ID", "org:acme-demo")}
    `)}
    ${renderSection("Integrations", `
      <div class="action-row">
        ${renderDisabledAction("GRC Connector", "Planned")}
        ${renderDisabledAction("CI/CD Release Gate", "Planned")}
      </div>
    `)}
    ${renderSection("Users & Roles", `
      <p style="font-size:12px;color:var(--muted)">Users and roles are planned for the compliance release.</p>
    `)}
  `;
  loadApiKeys();
}

function saveSettingsToken() {
  const val = q("#settings-token").value.trim();
  S.token = val;
  localStorage.setItem("notaryApiToken", val);
  notify("Token saved", "success");
  S.authConfigured = null;
  R();
}

async function loadApiKeys() {
  const list = q("#api-keys-list");
  try {
    const keys = await apiGet("/v1/platform/keys");
    list.innerHTML = keys.length ? renderTable(["Label", "Type", "Scopes", "Created", "Status", "Actions"], keys.map(k => [
      esc(k.label || "—"),
      k.key_type,
      (k.scopes || []).join(", "),
      k.created_at,
      k.revoked ? '<span class="badge badge-red">revoked</span>' : '<span class="badge badge-built">active</span>',
      `<button class="btn btn-sm btn-outline" onclick="revokeApiKey('${k.id}')">Revoke</button>`,
    ])) : `<p style="font-size:12px;color:var(--muted)">No API keys yet.</p>`;
  } catch (e) {
    list.innerHTML = `<p style="font-size:12px;color:var(--red)">Could not load keys: ${esc(e.message)}</p>`;
  }
}

async function createApiKey() {
  try {
    const r = await apiPostForm("/v1/platform/keys", {label: "Platform key " + new Date().toLocaleTimeString(), key_type: "api"});
    renderDrawer("API Key Created", `
      <p style="font-size:12px;color:var(--muted)">Store this key — it will only be shown once.</p>
      ${renderCodeBlock(r.key)}
    `);
    loadApiKeys();
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function revokeApiKey(keyId) {
  try {
    await apiPost("/v1/platform/keys/" + keyId + "/revoke");
    notify("Key revoked", "success");
    loadApiKeys();
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

// --- Init ---

function init() {
  setupNav();
  const savedEnv = localStorage.getItem("np-env");
  if (savedEnv) {
    S.env = savedEnv;
    q("#env-select").value = savedEnv;
  }
  const params = new URLSearchParams(location.search);
  if (params.get("view")) {
    S.view = params.get("view");
  }
  R();
}

document.addEventListener("DOMContentLoaded", init);
