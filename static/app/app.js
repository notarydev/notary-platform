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
  harborlineSeed: null,
  loading: false,
  error: null,
  setupStep: 0,
  setupWorkflowConfirmed: false,
  setupSystems: null,
  setupCaptureMethod: null,
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

async function apiPut(path, body, opts = {}) {
  const res = await fetch(path, {
    method: "PUT",
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
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("json")) return res.json();
  return null;
}

async function apiPostForm(path, params, opts = {}) {
  const url = path + "?" + new URLSearchParams(params).toString();
  return apiPost(url, {}, opts);
}

async function downloadProofBlob(incidentId, proofId, format) {
  const url = (format === "pdf"
    ? "/v1/incidents/" + encodeURIComponent(incidentId) + "/certificates/" + encodeURIComponent(proofId) + "/export-pdf"
    : "/v1/incidents/" + encodeURIComponent(incidentId) + "/certificates/" + encodeURIComponent(proofId) + "/download");
  try {
    const res = await fetch(url, {headers: authHeaders()});
    if (!res.ok) { const text = await res.text(); throw new Error(text); }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "proof_" + incidentId + "." + (format === "pdf" ? "pdf" : "json");
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function() { URL.revokeObjectURL(a.href); }, 1000);
  } catch (e) {
    notify("Download failed: " + e.message, "error");
  }
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
  const [view, query] = v.split("?");
  S.view = view;
  S.viewParams = {};
  if (query) {
    const params = new URLSearchParams(query);
    params.forEach((value, key) => { S.viewParams[key] = value; });
  }
  qa(".nav-item[data-view]").forEach((x) => x.classList.remove("active"));
  const b = q(`.nav-item[data-view="${view}"]`);
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
    } else if (S.view === "integrations") {
      renderIntegrations(c);
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
    } else if (S.view === "about") {
      renderAbout(c);
    } else if (S.view === "evidence") {
      const vrs = await apiGet("/v1/verification-records");
      renderEvidence(c, vrs);
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
    evidence: "Evidence",
    about: "About",
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
    { color: "var(--green)", icon: "✓", value: sh.sdk_installed ? "Yes" : "No", label: "SDK Installed", action: "nav('setup')" },
    { color: "var(--accent)", icon: "◆", value: sh.agents_instrumented || 0, label: "Agents", action: "nav('setup')" },
    { color: "var(--purple)", icon: "◎", value: `${sh.systems_connected || 0}/${sh.systems_total || 0}`, label: "Systems", action: "nav('setup')" },
    { color: "var(--blue)", icon: "◈", value: sh.capture_policies || 0, label: "Policies", action: "nav('readiness')" },
    { color: "var(--amber)", icon: "⚠", value: h.vrs_requires_label || 0, label: "Need Label", action: "nav('verification-records?filter=needs_label')" },
    { color: "var(--green)", icon: "✓", value: h.proofs_issued || 0, label: "Proofs", action: "nav('proofs')" },
  ];

  c.innerHTML = `
    ${renderHarborlineJourney()}
    ${h.is_demo ? `<div style="margin-bottom:16px;font-size:12px;color:var(--amber);font-weight:600">${badgeDemo()} Fictional demo data — no production or customer data.</div>` : ""}
    <div class="stat-grid">${stats.map(s => `
      <div class="stat stat-clickable" onclick="${s.action}">
        <div style="color:${s.color};font-size:12px;font-weight:700;margin-bottom:4px">${s.icon}</div>
        <div class="stat-val" style="color:${s.color}">${s.value}</div>
        <div class="stat-label">${s.label}</div>
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

function renderHarborlineJourney() {
  const seeded = S.harborlineSeed;
  const steps = seeded ? [
    { name: "Capture", detail: "Sealed Harborline loan decision", data: [
      ["Applicant", "HLCU-PL-0427"],
      ["Original decision", "DENY"],
      ["Expected outcome", "UNDERWRITING_REVIEW"],
      ["Root hash", (seeded.proof_of_mitigation_certificate_id || "n/a").slice(0, 16) + "..."],
    ], action: ["openVRDetail", seeded.verification_record_id] },
    { name: "Replay", detail: "Original DENY reproduced", data: [
      ["Original", "DENY"],
      ["Replayed", "DENY"],
      ["Verdict", "Failure reproduced from cassette"],
    ], action: ["openVRDetail", seeded.verification_record_id] },
    { name: "Fix", detail: "Corrected path routes to underwriting review", data: [
      ["Before fix", "DENY"],
      ["After fix", "UNDERWRITING_REVIEW"],
      ["Change", "Missing bureau evidence routes to underwriting review"],
    ], action: ["openIncidentDetail", seeded.incident_id] },
    { name: "Proof", detail: "Scenario-scoped mitigation proof", data: [
      ["Proof ID", seeded.proof_of_mitigation_certificate_id],
      ["Signature", "Verified"],
      ["Scope", "Verified for this scenario only"],
    ], action: ["openProofDetail", seeded.proof_of_mitigation_certificate_id] },
    { name: "Scenario", detail: "Regression scenario promoted", data: [
      ["Scenario ID", seeded.scenario_id],
      ["Library", "Release gate regression library"],
      ["Expected outcome", "UNDERWRITING_REVIEW"],
    ], action: ["openScenarioDetail", seeded.scenario_id] },
    { name: "Gate", detail: "Fail before fix, pass after fix", data: [
      ["Before fix", "FAIL"],
      ["After fix", "PASS"],
      ["Result", "Known failure covered by release gate"],
    ], action: ["openReleaseGateDetail", seeded.release_gate_after_fix_id] },
  ] : [
    { name: "Capture", detail: "Seal the AI decision evidence" },
    { name: "Replay", detail: "Reproduce the original decision from cassette" },
    { name: "Fix", detail: "Run the scenario-scoped fix" },
    { name: "Proof", detail: "Issue a tamper-evident mitigation proof" },
    { name: "Scenario", detail: "Promote to release gate regression library" },
    { name: "Gate", detail: "Block before fix, pass after fix" },
  ];
  return `
    <section class="golden-path">
      <div class="golden-copy">
        <div class="eyebrow">Harborline Credit Union · Member Lending Decision Assurance</div>
        <h2>Release Gate golden path</h2>
        <p>Thin-file applicant was denied when missing bureau evidence should have routed to underwriting review. The demo uses sealed cassette evidence and shows the release blocked before the fix, then passing after the scenario-scoped fix.</p>
        <div class="action-row">
          <button class="btn btn-green" onclick="seedHarborlineGoldenPath()">Seed Harborline Path</button>
          ${seeded ? `<button class="btn btn-outline" onclick="openVRDetail('${seeded.verification_record_id}')">Open Record</button>
          <button class="btn btn-outline" onclick="openReleaseGateDetail('${seeded.release_gate_before_fix_id}')">Blocked Gate</button>
          <button class="btn" onclick="openReleaseGateDetail('${seeded.release_gate_after_fix_id}')">Passing Gate</button>` : `<button class="btn btn-outline" onclick="nav('setup')">Open Setup</button>`}
        </div>
      </div>
      <div class="golden-panel">
        <div class="golden-panel-top">
          <span>${seeded ? "Seeded" : "Ready to seed"}</span>
          ${seeded ? `${statusBadge(seeded.release_gate_before_fix_status)} ${statusBadge(seeded.release_gate_after_fix_status)}` : badgeDemo()}
        </div>
        <div class="golden-steps">
          ${steps.map((step, idx) => {
            const stateClasses = ["state-capture", "state-replay", "state-fix", "state-proof", "state-scenario", idx === 5 && seeded ? "state-gate-pass" : idx === 5 ? "state-gate-fail" : "state-gate-fail"];
            const cls = (seeded ? "done " + (stateClasses[idx] || "done") : "");
            return `
            <div class="golden-step ${cls}" ${step.action ? `onclick="${step.action[0]}('${step.action[1]}')"` : ""}>
              <div class="golden-index">${idx + 1}</div>
              <div>
                <strong>${esc(step.name)}</strong>
                <p>${esc(step.detail)}</p>
                ${step.data ? `<div class="golden-step-data">${step.data.map(([k, v]) => `<span><strong>${esc(k)}:</strong> ${esc(v)}</span>`).join("")}</div>` : ""}
              </div>
            </div>`;
          }).join("")}
        </div>
      </div>
    </section>`;
}

async function seedHarborlineGoldenPath() {
  try {
    const r = await apiPost("/v1/demo/harborline-release-gate/seed");
    S.harborlineSeed = r;
    notify("Harborline path ready: gate " + r.release_gate_before_fix_status + " -> " + r.release_gate_after_fix_status, "success");
    R();
  } catch (e) {
    notify("Harborline seed failed: " + e.message, "error");
  }
}

function openReleaseGateDetail(id) {
  S.selectedReleaseGate = id;
  nav("release-gate-detail");
}

// --- INTEGRATIONS & CAPTURE ---

async function renderIntegrations(c) {
  if (!S._ic_experience_chosen) {
    c.innerHTML = renderIntegrationsChooseExperience();
    return;
  }
  c.innerHTML = sk(40);
  const systems = await apiGet("/v1/setup/ai-systems").catch(() => []);
  const status = await apiGet("/v1/setup/status").catch(() => ({}));
  const selectedSystemId = S._ic_selected_system;
  const editing = S._ic_editing;
  c.innerHTML = `
    <h2 style="margin-bottom:4px">Integrations & Capture</h2>
    <p class="section-sub" style="margin-bottom:16px">Connect AI systems and configure how Notary receives and handles decision evidence.</p>
    ${renderIntegrationsStats(status)}
    <div id="ic-workspace">
      ${editing ? renderIntegrationsForm() : (
        selectedSystemId ? renderAISystemDetail(selectedSystemId) : renderIntegrationsSystemList(systems)
      )}
    </div>`;
}

function renderIntegrationsChooseExperience() {
  return `
    <h2 style="margin-bottom:20px">Welcome to Notary</h2>
    <p style="font-size:14px;color:var(--muted);margin-bottom:24px;max-width:600px">Choose how you want to get started with AI Decision Assurance.</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:720px">
      <div class="ic-experience-card" onclick="nav('home')" style="cursor:pointer">
        <div class="ic-experience-icon">▶</div>
        <h3>Explore Harborline Demo</h3>
        <p>See Notary in action with our preconfigured lending scenario. Walk through the full assurance loop — capture, replay, fix, proof, and release gate.</p>
        <span class="badge badge-demo" style="margin-top:12px">GUIDED DEMO</span>
      </div>
      <div class="ic-experience-card ic-experience-primary" onclick="S._ic_experience_chosen=true;renderIntegrations(q('#main-content'))" style="cursor:pointer">
        <div class="ic-experience-icon">⚙</div>
        <h3>Set Up Your Organization</h3>
        <p>Register your AI systems, connect capture sources, and configure evidence handling. No assumptions about your industry or workflow.</p>
        <span class="badge badge-built" style="margin-top:12px">GET STARTED</span>
      </div>
    </div>
    <p style="font-size:11px;color:var(--dim);margin-top:20px">Harborline demo is a guided walkthrough. Customer onboarding starts with zero assumptions.</p>`;
}

function renderIntegrationsStats(status) {
  const total = status.total_systems || 0;
  const active = status.active_systems || 0;
  const inSetup = (status.systems_in_setup || []).length;
  return `
    <div style="display:flex;gap:12px;margin-bottom:16px">
      <div class="stat"><div class="stat-val">${total}</div><div class="stat-label">AI Systems</div></div>
      <div class="stat"><div class="stat-val" style="color:var(--green)">${active}</div><div class="stat-label">Active</div></div>
      <div class="stat"><div class="stat-val" style="color:var(--amber)">${inSetup}</div><div class="stat-label">In Setup</div></div>
    </div>`;
}

function renderIntegrationsForm(system) {
  const s = system || {};
  return `
    <div class="ic-form-card">
      <h3 style="margin-bottom:12px">${s.id ? "Edit AI System" : "Register an AI System"}</h3>
      <div class="np-form">
        <div class="integ-form-row">
          <div class="np-field" style="flex:2"><label>System Name *</label><input id="ais-name" value="${esc(s.name || "")}" placeholder="e.g. Claims Review Assistant"></div>
          <div class="np-field" style="flex:1"><label>System Type *</label>
            <select id="ais-type">
              <option value="agent" ${s.system_type === "agent" ? "selected" : ""}>Agent</option>
              <option value="model_service" ${s.system_type === "model_service" ? "selected" : ""}>Model Service</option>
              <option value="decision_engine" ${s.system_type === "decision_engine" ? "selected" : ""}>Decision Engine</option>
              <option value="ai_enabled_app" ${s.system_type === "ai_enabled_app" ? "selected" : ""}>AI-Enabled App</option>
            </select>
          </div>
        </div>
        <div class="integ-form-row">
          <div class="np-field" style="flex:1"><label>Deployment / Version</label><input id="ais-version" value="${esc(s.deployment_version || "")}" placeholder="e.g. v2.1.0"></div>
          <div class="np-field" style="flex:2"><label>Decision Endpoint</label><input id="ais-endpoint" value="${esc(s.decision_endpoint || "")}" placeholder="e.g. /claims/recommendation"></div>
        </div>
        <div class="integ-form-row">
          <div class="np-field" style="flex:1"><label>Business Owner</label><input id="ais-bo" value="${esc(s.business_owner || "")}"></div>
          <div class="np-field" style="flex:1"><label>Technical Owner</label><input id="ais-to" value="${esc(s.technical_owner || "")}"></div>
        </div>
        <div class="np-field"><label>Uses external tools / APIs?</label>
          <label style="font-size:12px;font-weight:400;display:flex;align-items:center;gap:8px;margin-top:4px">
            <input type="checkbox" id="ais-external" ${s.external_caller ? "checked" : ""}> Yes, this system calls external services
          </label>
        </div>
        <div class="action-row" style="margin-top:12px">
          <button class="btn btn-green" onclick="saveAISystem('${s.id || ""}')">${s.id ? "Save Changes" : "Register System"}</button>
          <button class="btn btn-outline" onclick="S._ic_editing=null;renderIntegrations(q('#main-content'))">Cancel</button>
        </div>
      </div>
    </div>`;
}

async function saveAISystem(existingId) {
  const name = q("#ais-name").value.trim();
  if (!name) { notify("System name is required", "error"); return; }
  const body = {
    name,
    system_type: q("#ais-type").value,
    deployment_version: q("#ais-version").value,
    decision_endpoint: q("#ais-endpoint").value,
    business_owner: q("#ais-bo").value,
    technical_owner: q("#ais-to").value,
    external_caller: q("#ais-external").checked,
  };
  try {
    if (existingId) {
      await apiPut("/v1/setup/ai-systems/" + existingId, body);
      notify("System updated", "success");
    } else {
      await apiPost("/v1/setup/ai-systems", body);
      notify("System registered", "success");
    }
    S._ic_editing = null;
    renderIntegrations(q("#main-content"));
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

function renderIntegrationsSystemList(systems) {
  return `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div class="section-title" style="margin:0">AI Systems</div>
      <button class="btn btn-sm" onclick="S._ic_editing={};renderIntegrations(q('#main-content'));q('#ic-workspace').scrollIntoView({behavior:'smooth'})">+ Register System</button>
    </div>
    ${systems.length === 0 ? `
      <div class="empty-state" style="border:1px dashed var(--border);border-radius:var(--radius);padding:32px">
        <h3>No AI systems registered yet</h3>
        <p>Register your first AI system to begin setting up capture and evidence handling.</p>
        <button class="btn" onclick="S._ic_editing={};renderIntegrations(q('#main-content'))">Register Your First System</button>
      </div>
    ` : `
    <div style="display:grid;gap:10px">
      ${systems.map(s => `
        <div class="ic-system-row" onclick="S._ic_selected_system='${s.id}';renderIntegrations(q('#main-content'))">
          <div style="display:flex;align-items:center;gap:12px;flex:1">
            <div class="ic-system-icon">${s.system_type === "agent" ? "🤖" : s.system_type === "model_service" ? "⚡" : s.system_type === "decision_engine" ? "⚙" : "📱"}</div>
            <div>
              <strong>${esc(s.name)}</strong>
              <div style="font-size:11px;color:var(--muted)">${esc(s.system_type)} · ${s.deployment_version ? esc(s.deployment_version) : "no version"}</div>
            </div>
          </div>
          <span class="badge badge-${s.status === "active" ? "green" : s.status === "draft" ? "planned" : s.status === "error" ? "red" : "ingested"}">${esc(s.status)}</span>
          <span style="color:var(--dim);font-size:16px">→</span>
        </div>
      `).join("")}
    </div>`}`;
}

async function renderAISystemDetail(systemId) {
  const [system, connectors, fieldRules, validationRuns] = await Promise.all([
    apiGet("/v1/setup/ai-systems/" + systemId).catch(() => null),
    apiGet("/v1/setup/ai-systems/" + systemId + "/connectors").catch(() => []),
    apiGet("/v1/setup/ai-systems/" + systemId + "/field-rules").catch(() => []),
    apiGet("/v1/setup/ai-systems/" + systemId + "/validation-runs").catch(() => []),
  ]);
  if (!system) { notify("System not found", "error"); S._ic_selected_system = null; renderIntegrations(q("#main-content")); return; }
  const c = q("#ic-workspace");
  if (!c) return;

  const lastValidation = validationRuns.length > 0 ? validationRuns[validationRuns.length - 1] : null;
  const coverage = lastValidation ? JSON.parse(lastValidation.coverage_json || "{}") : {};
  const tab = S._ic_system_tab || "connectors";

  c.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <button class="btn btn-outline btn-sm" onclick="S._ic_selected_system=null;S._ic_system_tab=null;renderIntegrations(q('#main-content'))">← Back</button>
      <h3 style="margin:0">${esc(system.name)}</h3>
      <span class="badge badge-${system.status === "active" ? "green" : system.status === "draft" ? "planned" : system.status === "error" ? "red" : "ingested"}">${esc(system.status)}</span>
      <button class="btn btn-outline btn-sm" onclick="S._ic_editing=${JSON.stringify(system).replace(/"/g, "'")};renderAISystemDetail('${systemId}')">Edit</button>
    </div>
    <div class="integ-tabs">
      <button class="integ-tab ${tab === "connectors" ? "active" : ""}" onclick="S._ic_system_tab='connectors';renderAISystemDetail('${systemId}')">Connectors ${connectors.length ? `<span class="tab-badge">${connectors.length}</span>` : ""}</button>
      <button class="integ-tab ${tab === "evidence" ? "active" : ""}" onclick="S._ic_system_tab='evidence';renderAISystemDetail('${systemId}')">Evidence Graph</button>
      <button class="integ-tab ${tab === "boundary" ? "active" : ""}" onclick="S._ic_system_tab='boundary';renderAISystemDetail('${systemId}')">Boundary ${fieldRules.length ? `<span class="tab-badge">${fieldRules.length}</span>` : ""}</button>
      <button class="integ-tab ${tab === "validation" ? "active" : ""}" onclick="S._ic_system_tab='validation';renderAISystemDetail('${systemId}')">Validate & Activate</button>
    </div>
    <div id="ic-tab-content">
      ${tab === "connectors" ? renderConnectorsTab(system, connectors) : ""}
      ${tab === "evidence" ? renderEvidenceTab(system) : ""}
      ${tab === "boundary" ? renderBoundaryTab(system, fieldRules) : ""}
      ${tab === "validation" ? renderValidationTab(system, coverage, validationRuns) : ""}
    </div>`;
}

function renderConnectorsTab(system, connectors) {
  const addingConnector = S._ic_adding_connector;
  return `
    <div style="display:flex;justify-content:space-between;align-items:center;margin:16px 0 12px">
      <div class="section-title" style="margin:0">Capture Sources</div>
      <button class="btn btn-sm" onclick="S._ic_adding_connector=true;renderAISystemDetail('${system.id}')">+ Add Capture Source</button>
    </div>
    ${addingConnector ? `
      <div class="ic-connector-form">
        <div class="integ-form-row">
          <div class="np-field" style="flex:1"><label>Connector Type *</label>
            <select id="conn-type">
              <option value="python_sdk">Python SDK</option>
              <option value="rest_api">REST API</option>
              <option value="webhook">Webhook</option>
              <option value="event_stream">Event Stream</option>
              <option value="manual">Manual Submission</option>
              <option value="batch_import">File / Batch Import</option>
            </select>
          </div>
          <div class="np-field" style="flex:2"><label>Name</label><input id="conn-name" placeholder="e.g. Production Agent SDK"></div>
        </div>
        <div class="action-row" style="margin-top:8px">
          <button class="btn btn-green btn-sm" onclick="saveConnector('${system.id}')">Create Connector</button>
          <button class="btn btn-outline btn-sm" onclick="S._ic_adding_connector=null;renderAISystemDetail('${system.id}')">Cancel</button>
        </div>
      </div>
    ` : ""}
    ${connectors.length === 0 ? `
      <div class="empty-state" style="border:1px dashed var(--border);border-radius:var(--radius);padding:24px">
        <p>No capture sources connected yet. Add a connector to start receiving decision evidence.</p>
      </div>
    ` : `
    <div style="display:grid;gap:8px">
      ${connectors.map(c => `
        <div class="ic-connector-row">
          <div style="flex:1">
            <strong>${esc(c.name || c.connector_type)}</strong>
            <div style="font-size:11px;color:var(--muted)">${esc(c.connector_type)}${c.last_tested_at ? " · last tested " + esc(c.last_tested_at) : ""}</div>
          </div>
          <span class="badge badge-${c.status === "connected" ? "green" : c.status === "error" ? "red" : c.status === "receiving" ? "replayed" : c.status === "validated" ? "certified" : "planned"}">${esc(c.status)}</span>
          <div class="action-row">
            <button class="btn btn-outline btn-sm" onclick="testConnector('${c.id}','${system.id}')">Test</button>
            <button class="btn btn-outline btn-sm" onclick="viewConnectorSamples('${c.id}','${system.id}')">View Sample</button>
          </div>
        </div>
      `).join("")}
    </div>`}`;
}

async function saveConnector(systemId) {
  const type = q("#conn-type").value;
  const name = q("#conn-name").value.trim();
  try {
    await apiPost("/v1/setup/ai-systems/" + systemId + "/connectors", { connector_type: type, name: name || type, config: {} });
    notify("Connector created", "success");
    S._ic_adding_connector = null;
    renderAISystemDetail(systemId);
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function testConnector(connId, systemId) {
  try {
    const r = await apiPost("/v1/setup/connectors/" + connId + "/test", {});
    notify(r.message || "Connection verified", "success");
    renderAISystemDetail(systemId);
  } catch (e) {
    notify("Test failed: " + e.message, "error");
  }
}

async function viewConnectorSamples(connId, systemId) {
  try {
    const samples = await apiGet("/v1/setup/connectors/" + connId + "/samples");
    if (!samples || samples.length === 0) {
      notify("No samples available yet", "info");
      return;
    }
    S._ic_selected_sample = samples[0];
    S._ic_system_tab = "evidence";
    renderAISystemDetail(systemId);
  } catch (e) {
    notify("Failed to load samples: " + e.message, "error");
  }
}

function renderEvidenceTab(system) {
  const sample = S._ic_selected_sample;
  return `
    <div style="margin:16px 0">
      <div class="section-title" style="margin:0 0 8px">Inspect Captured Evidence</div>
      <p class="section-sub">After a decision arrives, Notary detects the evidence flow through your system. Review what was captured.</p>
      ${sample ? `
        <div class="ic-evidence-header">
          <div><strong>Sample:</strong> ${esc(sample.summary)}</div>
          <div style="font-size:11px;color:var(--muted)">${esc(sample.timestamp)} · ${esc(sample.source_system)}</div>
        </div>
        <div class="ic-evidence-graph">
          <div class="ic-evidence-node">
            <div class="ic-evidence-node-header"><span>Inputs</span><span class="ic-evidence-node-type">source</span></div>
            <div class="ic-evidence-node-items">Application data, User context</div>
          </div>
          <div class="ic-evidence-arrow">↓</div>
          <div class="ic-evidence-node">
            <div class="ic-evidence-node-header"><span>Model / Agent</span><span class="ic-evidence-node-type" style="background:rgba(59,130,212,.15);color:#3b82d4">process</span></div>
            <div class="ic-evidence-node-items">Agent version · Prompt/configuration</div>
          </div>
          <div class="ic-evidence-arrow">↓ ↑</div>
          <div class="ic-evidence-node">
            <div class="ic-evidence-node-header"><span>Tool Responses</span><span class="ic-evidence-node-type" style="background:rgba(245,158,11,.15);color:#f59e0b">external</span></div>
            <div class="ic-evidence-node-items">Enrichment API · Policy service</div>
          </div>
          <div class="ic-evidence-arrow">↓</div>
          <div class="ic-evidence-node">
            <div class="ic-evidence-node-header"><span>Policy / Config</span><span class="ic-evidence-node-type" style="background:rgba(124,92,216,.15);color:#7c5cd8">config</span></div>
            <div class="ic-evidence-node-items">Policy version · Rules applied</div>
          </div>
          <div class="ic-evidence-arrow">↓</div>
          <div class="ic-evidence-node">
            <div class="ic-evidence-node-header"><span>Decision</span><span class="ic-evidence-node-type" style="background:rgba(34,197,94,.15);color:#22c55e">output</span></div>
            <div class="ic-evidence-node-items">Final outcome</div>
          </div>
        </div>
        <div class="section-title" style="margin-top:16px">Captured Elements</div>
        <div class="evidence-table">
          <table>
            <thead><tr><th>Kind</th><th>Source</th><th>Summary</th><th>Classification</th><th>Influenced</th><th>Sealed</th></tr></thead>
            <tbody>
              ${(sample.elements || []).map(e => `
                <tr>
                  <td><span class="badge badge-${e.kind === "decision" ? "green" : e.kind === "input" ? "planned" : e.kind === "model_invocation" ? "replayed" : "ingested"}">${esc(e.kind)}</span></td>
                  <td>${esc(e.source)}</td>
                  <td>${esc(e.summary)}</td>
                  <td>${esc(e.classification)}</td>
                  <td>${e.influenced_decision ? "✓" : "—"}</td>
                  <td>${e.sealed ? "✓" : "—"}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : `
        <div class="empty-state" style="border:1px dashed var(--border);border-radius:var(--radius);padding:24px">
          <p>No captured evidence to inspect yet. Connect a capture source and send a test decision to see the evidence graph.</p>
        </div>
      `}
    </div>`;
}

function renderBoundaryTab(system, rules) {
  const editingRules = S._ic_editing_rules;
  return `
    <div style="margin:16px 0">
      <div class="section-title" style="margin:0 0 8px">Evidence Handling Rules</div>
      <p class="section-sub">Define how Notary should handle each type of evidence. A system or field belongs in the decision boundary when it satisfies at least one criterion below.</p>
      <div class="ic-boundary-criteria">
        <div class="ic-criterion">✓ It supplied data consumed by the AI.</div>
        <div class="ic-criterion">✓ Its output materially influenced the decision.</div>
        <div class="ic-criterion">✓ It identifies the model, prompt, agent, policy or configuration version.</div>
        <div class="ic-criterion">✓ It contains the final AI decision.</div>
        <div class="ic-criterion">✓ It provides the authoritative expected outcome or later correction.</div>
        <div class="ic-criterion">✓ It is required to reproduce an external interaction.</div>
        <div class="ic-criterion">✓ It establishes provenance or chain of custody.</div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin:16px 0 8px">
        <div class="section-title" style="margin:0">Field Rules</div>
        <button class="btn btn-sm" onclick="S._ic_editing_rules=true;renderAISystemDetail('${system.id}')">${rules.length ? "Edit Rules" : "Define Rules"}</button>
      </div>
      ${editingRules ? renderFieldRulesForm(system, rules) : (
        rules.length === 0 ? `
          <div class="empty-state" style="border:1px dashed var(--border);padding:16px;border-radius:var(--radius)">
            <p>No field handling rules defined yet. Define how each evidence field should be stored, redacted, or excluded.</p>
          </div>
        ` : `
        <div class="evidence-table">
          <table>
            <thead><tr><th>Field Pattern</th><th>Action</th><th>Retention</th><th>Sensitive</th><th>Use for Replay</th></tr></thead>
            <tbody>
              ${rules.map(r => `
                <tr>
                  <td><code>${esc(r.field_pattern)}</code></td>
                  <td><span class="badge badge-${r.action === "store" ? "green" : r.action === "redact" ? "amber" : r.action === "hash" ? "replayed" : r.action === "exclude" ? "red" : "ingested"}">${esc(r.action)}</span></td>
                  <td>${r.retention_days}d</td>
                  <td>${r.sensitive ? "✓" : "—"}</td>
                  <td>${r.use_for_replay ? "✓" : "—"}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>`
      )}
    </div>`;
}

function renderFieldRulesForm(system, existingRules) {
  const defaults = existingRules.length > 0 ? existingRules : [
    {field_pattern: "input.*", action: "store", retention_days: 365, sensitive: false, use_for_replay: true},
    {field_pattern: "model_invocation.*", action: "store", retention_days: 365, sensitive: false, use_for_replay: true},
    {field_pattern: "tool_response.*", action: "store", retention_days: 365, sensitive: true, use_for_replay: true},
    {field_pattern: "policy_config.*", action: "store", retention_days: 730, sensitive: false, use_for_replay: true},
    {field_pattern: "decision.*", action: "store", retention_days: 2555, sensitive: false, use_for_replay: true},
    {field_pattern: "personal_data.*", action: "redact", retention_days: 90, sensitive: true, use_for_replay: false},
  ];
  const rows = defaults.map((r, i) => `
    <div class="ic-fhr-row" data-idx="${i}">
      <input class="ic-fhr-field" value="${esc(r.field_pattern)}" placeholder="field pattern (e.g. input.*)">
      <select class="ic-fhr-action">
        <option value="store" ${r.action === "store" ? "selected" : ""}>Store</option>
        <option value="redact" ${r.action === "redact" ? "selected" : ""}>Redact</option>
        <option value="hash" ${r.action === "hash" ? "selected" : ""}>Hash</option>
        <option value="exclude" ${r.action === "exclude" ? "selected" : ""}>Exclude</option>
      </select>
      <input class="ic-fhr-retention" type="number" value="${r.retention_days}" style="width:60px" min="1"> days
      <label style="font-size:11px;white-space:nowrap"><input class="ic-fhr-sensitive" type="checkbox" ${r.sensitive ? "checked" : ""}> Sensitive</label>
      <label style="font-size:11px;white-space:nowrap"><input class="ic-fhr-replay" type="checkbox" ${r.use_for_replay ? "checked" : ""}> Replay</label>
    </div>
  `).join("");
  return `
    <div class="ic-fhr-editor">
      <p style="font-size:12px;color:var(--muted);margin-bottom:8px">Configure how each evidence field type should be handled. ${defaults.length > 0 && existingRules.length === 0 ? "Default rules suggested based on common patterns." : ""}</p>
      ${rows}
      <div class="action-row" style="margin-top:12px">
        <button class="btn btn-green btn-sm" onclick="saveFieldRules('${system.id}')">Save Rules</button>
        <button class="btn btn-outline btn-sm" onclick="S._ic_editing_rules=null;renderAISystemDetail('${system.id}')">Cancel</button>
      </div>
    </div>`;
}

async function saveFieldRules(systemId) {
  const rows = qa(".ic-fhr-row");
  const rules = Array.from(rows).map(row => ({
    field_pattern: row.querySelector(".ic-fhr-field").value,
    action: row.querySelector(".ic-fhr-action").value,
    retention_days: parseInt(row.querySelector(".ic-fhr-retention").value) || 365,
    sensitive: row.querySelector(".ic-fhr-sensitive").checked,
    use_for_replay: row.querySelector(".ic-fhr-replay").checked,
  }));
  try {
    await apiPut("/v1/setup/ai-systems/" + systemId + "/field-rules", rules);
    notify("Field rules saved", "success");
    S._ic_editing_rules = null;
    renderAISystemDetail(systemId);
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

function renderValidationTab(system, coverage, validationRuns) {
  const hasCoverage = coverage && coverage.replay_readiness;
  return `
    <div style="margin:16px 0">
      <div class="section-title" style="margin:0 0 8px">Capture Coverage Validation</div>
      <p class="section-sub">Run validation to assess whether the current setup produces complete, replayable evidence.</p>
      <div style="display:flex;gap:12px;margin-bottom:16px">
        <button class="btn" onclick="runValidation('${system.id}')">Run Validation</button>
        <button class="btn btn-green ${system.status === "active" ? "" : ""}" onclick="activateSystem('${system.id}')" ${system.status === "active" ? "disabled" : ""}>
          ${system.status === "active" ? "Capture Active ✓" : "Activate Capture"}
        </button>
      </div>
      ${hasCoverage ? `
        <div class="ic-coverage-report">
          <div class="section-title" style="margin:12px 0 8px">Coverage Report</div>
          <div class="ic-coverage-grid">
            <div class="ic-coverage-item ${coverage.decision_detected ? "ok" : "fail"}"><span>Decision detected</span><span>${coverage.decision_detected ? "✓" : "✗"}</span></div>
            <div class="ic-coverage-item ${coverage.input_captured ? "ok" : "fail"}"><span>Input evidence captured</span><span>${coverage.input_captured ? "✓" : "✗"}</span></div>
            <div class="ic-coverage-item ${coverage.model_version_captured ? "ok" : "fail"}"><span>Model/agent version captured</span><span>${coverage.model_version_captured ? "✓" : "✗"}</span></div>
            <div class="ic-coverage-item ${coverage.prompt_captured ? "ok" : "fail"}"><span>Prompt/configuration captured</span><span>${coverage.prompt_captured ? "✓" : "✗"}</span></div>
            <div class="ic-coverage-item ${coverage.tool_responses_available ? "ok" : "fail"}"><span>Tool responses available</span><span>${coverage.tool_responses_available ? "✓" : "✗"}</span></div>
            <div class="ic-coverage-item ${coverage.final_decision_captured ? "ok" : "fail"}"><span>Final decision captured</span><span>${coverage.final_decision_captured ? "✓" : "✗"}</span></div>
            <div class="ic-coverage-item ${coverage.root_hash_valid ? "ok" : "fail"}"><span>Root hash valid</span><span>${coverage.root_hash_valid ? "✓" : "✗"}</span></div>
            <div class="ic-coverage-item ${coverage.cassette_material_available ? "ok" : "fail"}"><span>Cassette material available</span><span>${coverage.cassette_material_available ? "✓" : "✗"}</span></div>
            <div class="ic-coverage-item ${coverage.expected_outcome_source_available ? "ok" : "fail"}"><span>Expected-outcome source available</span><span>${coverage.expected_outcome_source_available ? "✓" : "✗"}</span></div>
          </div>
          <div class="ic-readiness-badge">
            Replay readiness: <strong class="${coverage.replay_readiness === "insufficient_context" ? "text-red" : "text-green"}">${esc(coverage.replay_readiness)}</strong>
          </div>
          <p style="font-size:12px;color:var(--muted);margin-top:8px">${esc(coverage.assessment || "")}</p>
        </div>
      ` : validationRuns.length > 0 ? `
        <p style="font-size:12px;color:var(--muted)">Last validation run: ${esc(validationRuns[validationRuns.length - 1].status)}</p>
      ` : `
        <div class="empty-state" style="border:1px dashed var(--border);padding:16px;border-radius:var(--radius)">
          <p>No validation runs yet. Run validation to check capture coverage.</p>
        </div>
      `}
    </div>`;
}

async function runValidation(systemId) {
  try {
    const r = await apiPost("/v1/setup/ai-systems/" + systemId + "/validate", {});
    notify("Validation complete: " + (JSON.parse(r.coverage_json || "{}").replay_readiness || "unknown"), "success");
    renderAISystemDetail(systemId);
  } catch (e) {
    notify("Validation failed: " + e.message, "error");
  }
}

async function activateSystem(systemId) {
  try {
    await apiPut("/v1/setup/ai-systems/" + systemId, {status: "active"});
    notify("Capture activated for this system", "success");
    renderAISystemDetail(systemId);
  } catch (e) {
    notify("Activation failed: " + e.message, "error");
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
      <thead><tr><th>ID</th><th>Source</th><th>Decision</th><th>Captured Systems</th><th>Replayability</th><th>Label</th><th>Links</th><th>Actions</th></tr></thead>
      <tbody>${vrs.map(v => {
        const systems = [v.source_system_id, v.agent_id].filter(Boolean).map(s => `<span class="badge badge-built">${esc(s.replace(/^[^:]+:/, ""))}</span>`).join(" ");
        const links = [];
        if (v.promoted_to_incident) links.push(`<span class="link" onclick="openIncidentDetail('${v.promoted_to_incident}')">Incident</span>`);
        if (v.promoted_to_scenario) links.push(`<span class="link" onclick="openScenarioDetail('${v.promoted_to_scenario}')">Scenario</span>`);
        if (v.certificate_id) links.push(`<span class="link" onclick="openProofDetail('${v.certificate_id}')">Proof</span>`);
        return `
        <tr class="vr-row" data-rp="${esc(v.replayability)}" onclick="openVRDetail('${v.id}')">
          <td>${v.is_demo ? badgeDemo() : ""} <span class="link">${v.id}</span></td>
          <td><span class="badge badge-${v.source_type === "sdk_snapshot" ? "built" : "ingested"}">${v.source_type.replace(/_/g, " ")}</span></td>
          <td><span class="decision-pill decision-fail">${esc(v.original_decision || "—")}</span></td>
          <td>${systems || "—"}</td>
          <td>${statusBadge(v.replayability)}</td>
          <td>${v.current_label_id ? '<span class="badge badge-built">labeled</span>' : v.replayability === "requires_human_label" ? '<span class="badge badge-planned">needs label</span>' : '—'}</td>
          <td class="vr-links">${links.join(" ") || "—"}</td>
          <td class="action-row" onclick="event.stopPropagation()">
            ${v.replayability === "requires_human_label" ? `<button class="btn btn-sm btn-amber" onclick="openAddLabelForm('${v.id}')">Add Label</button>` : ""}
            ${v.replayability === "replayable" || v.replayability === "partially_replayable" ? `<button class="btn btn-sm" onclick="runVRReplay('${v.id}')">Replay</button>` : ""}
            ${v.replayability === "replayable" && v.current_label_id ? `<button class="btn btn-sm btn-green" onclick="promoteVR('${v.id}')">Promote</button>` : ""}
            ${v.replayability === "evidence_only" || v.replayability === "missing_context" ? `<button class="btn btn-sm btn-outline" onclick="openVRDetail('${v.id}')">Investigate</button>` : ""}
            <button class="btn btn-sm btn-outline" onclick="openVRDetail('${v.id}')">Detail</button>
          </td>
        </tr>`;
      }).join("")}
      </tbody>
    </table>
  `;
  // Default filter 'all' visible; filterVR toggles rows. Apply any view param filter.
  window._vrFilter = "all";
  if (S.viewParams && S.viewParams.filter) {
    setTimeout(() => filterVR(S.viewParams.filter), 0);
  }
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
    ${renderSection("Decision Evidence Graph", (v.events || []).length ? `
      <div class="evidence-graph">
        ${(function() {
          var groups = {};
          (v.events || []).forEach(function(e) {
            var key = e.source_system || e.kind;
            if (!groups[key]) groups[key] = [];
            groups[key].push(e);
          });
          return Object.keys(groups).map(function(system) {
            var evts = groups[system];
            return '<div class="evidence-node-group">' +
              '<div class="evidence-group-header">' + esc(system) + '</div>' +
              evts.sort(function(a, b) { return (a.order || 0) - (b.order || 0); }).map(function(ev) {
                var icon = ev.kind === "input" ? "📥" : ev.kind === "tool_call" ? "🔧" : ev.kind === "api_response" ? "📡" : ev.kind === "decision" ? "⚖" : ev.kind === "policy" ? "📋" : "●";
                var summary = ev.payload && (ev.payload.decision || ev.payload.response && ev.payload.response.status || ev.payload.version || ev.kind);
                return '<div class="evidence-node"><span class="evidence-icon">' + icon + '</span><span class="evidence-kind">' + esc(ev.kind) + '</span><span class="evidence-summary">' + esc(typeof summary === "string" ? summary : JSON.stringify(summary).substring(0, 60)) + '</span></div>';
              }).join('<div class="evidence-edge">↓</div>') +
            '</div>';
          }).join('<div class="evidence-edge-h">→</div>');
        })()}
      </div>
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
      <div class="np-field"><label>Expected Outcome</label><input id="label-outcome" placeholder="e.g. UNDERWRITING_REVIEW"></div>
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
  const pills = Object.keys(counts).map(k => ({key: k, label: k.replace(/^./, x => x.toUpperCase()) + " (" + counts[k] + ")", active: false, onClick: `filterIncidents('${k}')`, filter: k}));
  c.innerHTML = `
    ${renderFilterPills(pills)}
    <table>
      <thead><tr><th>Incident</th><th>Stage</th><th>Observed → Expected</th><th>Systems</th><th>R</th><th>F</th><th>C</th><th>Next Action</th></tr></thead>
      <tbody>${ix.map(i => {
        const obs = i.replay_result?.decision || i.snapshot_summary?.decision || "—";
        const exp = i.mutation_result?.expected_correct_behavior || i.snapshot_summary?.expected_outcome || "—";
        const systems = i.snapshot_summary?.systems || [];
        const systemStr = Array.isArray(systems) ? systems.length + " systems" : "—";
        const nextAct = !i.replay_result ? "Run Replay" : i.replay_result && !i.mutation_result ? "Verify Fix" : i.mutation_result && !i.certificate ? "Issue Proof" : "Investigate";
        return `
        <tr class="inc-row" data-status="${esc(i.status)}" onclick="openIncidentDetail('${i.incident_id}')">
          <td>${badgeDemo()} <span class="link">${i.incident_id}</span></td>
          <td>${statusBadge(i.status)}</td>
          <td><span class="decision-pill decision-fail">${esc(obs)}</span> → <span class="decision-pill decision-pass">${esc(exp)}</span></td>
          <td style="font-size:11px">${esc(systemStr)}</td>
          <td style="text-align:center">${i.replay_result && i.replay_result.replay_status === "replayed" ? '<span style="color:var(--green);font-weight:800">✓</span>' : '<span style="color:var(--dim)">—</span>'}</td>
          <td style="text-align:center">${i.mutation_result && i.mutation_result.mitigated ? '<span style="color:var(--green);font-weight:800">✓</span>' : i.mutation_result ? '<span style="color:var(--amber)">⚠</span>' : '<span style="color:var(--dim)">—</span>'}</td>
          <td style="text-align:center">${i.certificate && i.certificate.certificate_id ? '<span style="color:var(--green);font-weight:800">✓</span>' : '<span style="color:var(--dim)">—</span>'}</td>
          <td class="action-row" onclick="event.stopPropagation()">
            ${!i.replay_result ? `<button class="btn btn-sm" onclick="runIncidentReplay('${i.incident_id}')">Replay</button>` : ""}
            ${i.replay_result && !i.mutation_result ? `<button class="btn btn-sm btn-amber" onclick="runIncidentVerify('${i.incident_id}')">Verify Fix</button>` : ""}
            ${i.mutation_result && !i.certificate ? `<button class="btn btn-sm btn-green" onclick="runIncidentCertify('${i.incident_id}')">Issue Proof</button>` : ""}
            ${i.certificate ? `<button class="btn btn-sm btn-outline" onclick="openIncidentDetail('${i.incident_id}')">Investigate</button>` : ""}
          </td>
        </tr>`;
      }).join("")}
      </tbody>
    </table>
  `;
  window._incFilter = "all";
  if (S.viewParams && S.viewParams.filter) {
    setTimeout(() => filterIncidents(S.viewParams.filter), 0);
  }
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
  const [sourceVr, snapshot, replayEvents, labelData] = await Promise.all([
    apiGet("/v1/verification-records").then(function(vrs) { return vrs.find(function(v) { return v.promoted_to_incident === i.incident_id; }) || null; }).catch(function() { return null; }),
    apiGet("/v1/incidents/" + i.incident_id + "/snapshot").catch(function() { return null; }),
    (i.replay_result && i.replay_result.replay_run_id
      ? apiGet("/v1/replay-runs/" + encodeURIComponent(i.replay_result.replay_run_id) + "/events").catch(() => null)
      : Promise.resolve(null)),
  ]);
  const cert = i.certificate || {};
  let sigValid = null;
  if (cert.certificate_id) {
    sigValid = await apiGet(`/v1/incidents/${i.incident_id}/certificates/${cert.certificate_id}/verify`).then(r => r.signature_valid).catch(() => null);
  }
  const scenario = sourceVr?.scenario || sourceVr?.metadata?.scenario || {};
  const elements = Array.isArray(snapshot && snapshot.elements) ? snapshot.elements : [];
  const inputEl = elements.find(function(e) { return e.kind === "input"; }) || {};
  const httpEl = elements.find(function(e) { return e.kind === "http"; }) || {};
  const policyEl = elements.find(function(e) { return e.kind === "policy"; }) || {};
  const decisionEl = elements.find(function(e) { return e.kind === "decision"; }) || {};
  const applicantId = (inputEl.payload && inputEl.payload.applicant_id) || (sourceVr && sourceVr.source_record_ref) || "HLCU-PL-0427";
  const systemName = (sourceVr && sourceVr.source_system_id) || "—";
  const agentName = (sourceVr && sourceVr.agent_id) || "—";
  const agentVer = (sourceVr && sourceVr.agent_version) || "—";
  const policyVer = (policyEl.payload && (policyEl.payload.version || policyEl.payload.policy_version)) || (sourceVr && sourceVr.policy_version) || "—";
  const envName = (sourceVr && sourceVr.environment_id) || "—";
  const capturedAt = (sourceVr && sourceVr.created_at) || (i.snapshot_summary && i.snapshot_summary.timestamp) || "—";
  const originalDecision = (decisionEl.payload && decisionEl.payload.decision) || (i.replay_result && i.replay_result.decision) || (i.mutation_result && i.mutation_result.original_decision) || (sourceVr && sourceVr.expected_outcome) || "—";
  const replayedDecision = (i.replay_result && i.replay_result.decision) || "—";
  const fixedDecision = (i.mutation_result && i.mutation_result.mutated_decision) || (labelData && labelData.expected_outcome) || "—";
  const expectedOutcome = (labelData && labelData.expected_outcome) || (sourceVr && sourceVr.expected_outcome) || (i.mutation_result && i.mutation_result.expected_correct_behavior) || "—";
  const replayStatus = i.replay_result && i.replay_result.replay_status === "replayed" ? "pass" : i.replay_result && i.replay_result.replay_status === "error" ? "error" : "pending";
  const fixMitigated = i.mutation_result && i.mutation_result.mitigated;
  const proofError = wf.issue_proof_reason || (i.mutation_result && !i.mutation_result.mitigated ? "Fix did not produce expected outcome" : !i.mutation_result ? "Issue Proof requires a successful Fix Verification. Run Verify Fix after a successful replay." : "");
  const replayRows = Array.isArray(replayEvents) && replayEvents.length > 0
    ? replayEvents.sort((a, b) => (a.sequence || 0) - (b.sequence || 0)).map(ev => ({
        step: ev.step,
        source: ev.source,
        expected: ev.expected,
        actual: ev.actual,
        status: ev.status,
      }))
    : [
        { step: "Applicant facts loaded", source: "sealed input", expected: "match", actual: applicantId ? "match" : "—", status: applicantId ? "pass" : "pending", sequence: 0 },
        { step: "Build response cassette", source: "cassette", expected: "built", actual: "built", status: "pass", sequence: 1 },
        { step: "Agent decision produced", source: "replay", expected: originalDecision, actual: replayedDecision, status: replayStatus === "pass" ? "reproduced" : "pending", sequence: 2 },
        { step: "Replay verdict", source: "comparison", expected: "reproduce known failure", actual: replayStatus === "pass" ? "reproduced" : "pending", status: replayStatus, sequence: 3 },
      ];

  // Two-column replay workspace (Phase B)
  var selectedReplayIdx = S._selectedReplayIdx || 0;
  var selectedEvent = replayRows.length > 0 ? replayRows[selectedReplayIdx] || replayRows[0] : null;
  var replayColumnsHtml = replayRows.length > 0
    ? '<div class="replay-workspace"><div class="replay-timeline"><div class="section-sub" style="margin-bottom:8px">Execution Timeline</div>' + replayRows.map(function(ev, idx) {
        var icons = { pass: "✓", running: "⟳", reproduced: "✓", fail: "✗", error: "✗", pending: "○", escalation_required: "⚠", diverged: "✗" };
        var colors = { pass: "var(--green)", running: "var(--accent)", reproduced: "var(--green)", fail: "var(--red)", error: "var(--red)", pending: "var(--dim)", escalation_required: "var(--amber)", diverged: "var(--red)" };
        var ic = icons[ev.status] || "○";
        var cl = colors[ev.status] || "var(--dim)";
        var isSelected = idx === selectedReplayIdx;
        return '<div class="replay-event-row' + (isSelected ? " selected" : "") + '" onclick="selectReplayEvent(' + idx + ')"><div class="replay-event-icon" style="color:' + cl + ';border-color:' + cl + '">' + ic + '</div><div class="replay-event-body"><div class="replay-event-step">' + esc(ev.step) + '</div><div class="replay-event-status" style="color:' + cl + '">' + esc(ev.status) + '</div></div></div>';
      }).join("") + '<div style="margin-top:8px;font-size:10px;color:var(--dim);text-align:center">' + replayRows.length + ' events</div></div>' + (selectedEvent ? '<div class="replay-detail"><div class="section-sub" style="margin-bottom:8px">Event Detail</div>' + renderKV("Step", esc(selectedEvent.step)) + renderKV("Source", esc(selectedEvent.source || "—")) + renderKV("Expected", esc(selectedEvent.expected || "—")) + renderKV("Actual", esc(selectedEvent.actual || "—")) + renderKV("Status", '<span class="replay-status ' + selectedEvent.status + '">' + esc(selectedEvent.status) + '</span>') + renderKV("Sequence", "" + (selectedEvent.sequence != null ? selectedEvent.sequence : "—")) + renderKV("Timestamp", esc(selectedEvent.timestamp || "—")) + '</div>' : '') + '</div>'
    : '<div class="empty-state compact"><h3>No replay events</h3><p>Run Replay to generate execution events.</p></div>';

  // Custody audit trail (Phase C)
  var custodyHtml = "";
  if (i.custody && i.custody.length) {
    custodyHtml = '<div class="custody-timeline">' + i.custody.slice().reverse().map(function(ev) {
      return '<div class="custody-event"><span class="custody-time">' + esc(ev.timestamp) + '</span><span class="custody-action">' + esc(ev.action) + '</span><span class="custody-actor">' + esc(ev.actor) + '</span><span class="custody-detail">' + esc(ev.detail) + '</span></div>';
    }).join("") + "</div>";
  }

  // Tab badges
  function tabBadge(label, count, active) {
    return '<button class="incident-tab' + (active ? ' active' : '') + '" onclick="switchIncidentTab(\'' + label.toLowerCase() + '\')">' + esc(label) + (count ? ' <span class="tab-badge">' + count + '</span>' : '') + '</button>';
  }

  var tabs = [
    {id: "evidence", label: "Evidence", badge: elements.length || sourceVr ? String(elements.length || "✓") : ""},
    {id: "replay", label: "Replay", badge: i.replay_result ? (i.replay_result.replay_status === "replayed" ? "Reproduced" : "Ran") : ""},
    {id: "fix", label: "Fix", badge: fixMitigated ? "Passed" : i.mutation_result ? "Ran" : ""},
    {id: "proof", label: "Proof", badge: cert.certificate_id ? "Issued" : ""},
    {id: "gate", label: "Gate", badge: i.mutation_result && fixMitigated ? "Protected" : i.mutation_result ? "At Risk" : ""},
    {id: "audit", label: "Audit", badge: i.custody ? String(i.custody.length) : ""},
  ];
  var activeTab = S._incTab || "evidence";
  S._incTab = activeTab;

  // Fix detail
  var fixDetailHtml = "";
  if (i.mutation_result) {
    fixDetailHtml = '<div class="before-after"><div><span class="comparison-label">CAPTURED DECISION</span><strong class="decision-fail" style="display:block;font-size:18px;margin:8px 0">' + esc(i.mutation_result.original_decision || originalDecision) + '</strong><p>Known failure reproduced under the captured conditions.</p></div><div class="before-after-arrow">→</div><div><span class="comparison-label">AFTER FIX</span><strong class="text-green" style="display:block;font-size:18px;margin:8px 0">' + esc(i.mutation_result.mutated_decision || "—") + '</strong><p>' + (fixMitigated ? "Expected outcome verified for this scenario." : "Fix did not produce the expected outcome.") + '</p></div></div>' + renderKV("Expected outcome", esc(i.mutation_result.expected_correct_behavior || expectedOutcome)) + renderKV("Fix config", renderCodeBlock(JSON.stringify(i.mutation_result.fix_config || {}))) + renderKV("Decision changed", i.mutation_result.decision_changed ? "Yes" : "No");
  } else {
    fixDetailHtml = '<div class="empty-state compact"><h3>Fix verification pending</h3><p>Replay the failure first, then run the scenario-specific fix against the same cassette.</p></div>';
  }

  // Proof detail (Phase D)
  var proofDetailHtml = "";
  if (cert.certificate_id) {
    proofDetailHtml = '<div class="proof-bundle">' +
      '<h3>' + esc(cert.certificate_id) + '</h3>' +
      renderKV("Schema Version", esc(cert.schema_version || "pom-v1")) +
      renderKV("Incident", '<span class="link" onclick="openIncidentDetail(\'' + i.incident_id + '\')">' + i.incident_id + '</span>') +
      (sourceVr ? renderKV("Source V.R.", '<span class="link" onclick="openVRDetail(\'' + sourceVr.id + '\')">' + sourceVr.id + '</span>') : "") +
      renderKV("Original Decision", '<span class="decision-pill decision-fail">' + esc(originalDecision) + '</span>') +
      renderKV("Mutated Decision", '<span class="decision-pill decision-pass">' + esc(fixedDecision) + '</span>') +
      renderKV("Expected Outcome", esc(expectedOutcome || "Not available")) +
      renderKV("Replay Method", esc(cert.replay_method || "sealed cassette replay")) +
      renderKV("Root Hash", esc(cert.root_hash || (i.snapshot_summary && i.snapshot_summary.root_hash) || "—")) +
      renderKV("Signature", sigValid === true ? "✓ Valid" : sigValid === false ? "✗ Invalid" : "Unknown") +
      renderKV("Algorithm", esc(cert.signing_algorithm || "—")) +
      renderKV("Issued", esc(cert.timestamp || "—")) +
      renderKV("Claim Scope", esc(cert.claim_scope || "Verified fix for this tested scenario under recorded conditions. Does not certify general AI safety.")) +
      renderKV("Limitations", esc(cert.known_limitations || "None documented")) +
      '<div class="action-row" style="margin-top:12px">' +
      '<button class="btn btn-sm btn-outline" onclick="downloadProofBlob(\'' + i.incident_id + "','" + cert.certificate_id + "','json')" + '">Download JSON</button>' +
      '<button class="btn btn-sm btn-outline" onclick="downloadProofBlob(\'' + i.incident_id + "','" + cert.certificate_id + "','pdf')" + '">Download PDF</button>' +
      '<button class="btn btn-sm btn-outline" onclick="verifyIncidentCert(\'' + i.incident_id + '\')">Verify Signature</button>' +
      '</div></div>';
    if (sourceVr) {
      proofDetailHtml += renderSection("Promote to Scenario", '<p style="font-size:12px;color:var(--muted);margin-bottom:8px">This verified failure can be promoted to the scenario library for use in future release checks.</p><button class="btn btn-sm btn-outline" onclick="promoteToScenario(\'' + sourceVr.id + "','" + i.incident_id + '\')">Promote to Scenario</button>');
    }
  } else {
    proofDetailHtml = '<div class="proof-pending"><strong>No certificate issued</strong><p>' + esc(proofError || "Issue Proof becomes available after a mitigated Fix Verification.") + '</p></div>';
  }

  var gateHtml = '<div class="gate-impact"><span class="gate-node gate-capture">Captured</span><span class="gate-line"></span><span class="gate-node ' + (i.replay_result ? "gate-fail" : "gate-muted") + '">' + (i.replay_result ? "Blocked before fix" : "Replay pending") + '</span><span class="gate-line"></span><span class="gate-node ' + (fixMitigated ? "gate-pass" : "gate-muted") + '">' + (fixMitigated ? "Pass after fix" : "Fix pending") + '</span><span class="gate-line"></span><span class="gate-node ' + (cert.certificate_id ? "gate-pass" : "gate-muted") + '">' + (cert.certificate_id ? "Proof attached" : "Gate not updated") + '</span></div><p class="section-sub" style="margin-top:8px">A promoted scenario can block a release when this known failure reappears. This is scenario-scoped evidence, not a general AI safety claim.</p>';

  c.innerHTML = [
    '<button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav(\'incidents\')">← Back to Incidents</button>',
    badgeDemo(),
    '<div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">',
    statusBadge(i.status),
    '<span style="font-size:13px;color:var(--muted)">ID: ' + esc(i.incident_id) + '</span>',
    '</div>',
    // Phase C: separate captured/replayed/expected/after-fix summary
    '<section><div class="incident-summary-v2">',
    '<div class="summary-block"><span class="summary-block-label">Captured</span><strong>' + esc(originalDecision) + '</strong><span class="summary-block-source">from ' + esc(systemName) + '</span></div>',
    '<div class="summary-arrow">→</div>',
    '<div class="summary-block"><span class="summary-block-label">Replayed</span><strong>' + esc(replayedDecision || "Pending") + '</strong><span class="summary-block-source">' + (i.replay_result ? "via " + esc(i.replay_result.replay_status || "cassette") : "not yet replayed") + '</span></div>',
    '<div class="summary-arrow">→</div>',
    '<div class="summary-block"><span class="summary-block-label">Expected</span><strong class="text-green">' + esc(expectedOutcome || "—") + '</strong><span class="summary-block-source">' + (labelData ? "from label" : sourceVr && sourceVr.expected_outcome ? "from source" : "—") + '</span></div>',
    '<div class="summary-arrow">→</div>',
    '<div class="summary-block"><span class="summary-block-label">After Fix</span><strong class="text-green">' + esc(fixedDecision || "—") + '</strong><span class="summary-block-source">' + (fixMitigated ? "verified" : i.mutation_result ? "not verified" : "not attempted") + '</span></div>',
    '</div></section>',
    // Metadata section (Phase C)
    '<section><div class="section-title">Metadata</div><div class="incident-metadata">',
    renderKV("System", esc(systemName)),
    renderKV("Agent", esc(agentName)),
    renderKV("Agent Version", esc(agentVer)),
    renderKV("Policy Version", esc(policyVer)),
    renderKV("Environment", esc(envName)),
    renderKV("Captured", esc(capturedAt)),
    renderKV("Severity", "High"),
    renderKV("Owner", "Platform User"),
    '</div></section>',
    // Workflow
    renderSection("Progress", wf.steps.map(function(s) { return renderWorkflowStep(s.label, s.state, s.detail, s.action ? '<button class="btn btn-sm" onclick="wfAction(\'' + i.incident_id + '\', \'' + s.label + '\')">' + s.action + '</button>' : ""); }).join("")),
    // Tabs with badges
    '<div class="incident-tabs">',
    tabs.map(function(t) { return tabBadge(t.label, t.badge, t.id === activeTab); }).join(""),
    '</div>',
    '<div class="incident-tab-content">',
    activeTab === "evidence" ? renderSection("Captured Evidence", (elements.length ? '<div class="evidence-table"><table><thead><tr><th>#</th><th>Kind</th><th>Source System</th><th>Summary</th></tr></thead><tbody>' + elements.map(function(e, idx) {
      var summary = "";
      if (e.payload) {
        if (e.payload.decision) summary = e.payload.decision;
        else if (e.payload.response && typeof e.payload.response === "object") summary = e.payload.response.status || JSON.stringify(e.payload.response).slice(0, 60);
        else if (e.payload.version) summary = e.payload.version;
        else if (e.payload.applicant_id) summary = e.payload.applicant_id;
        else summary = e.kind;
      }
      return '<tr onclick="event.stopPropagation();renderDrawer(\'Element ' + (idx + 1) + '\', renderCodeBlock(JSON.stringify(e, null, 2)))"><td>' + (idx + 1) + '</td><td><span class="badge badge-built">' + esc(e.kind) + '</span></td><td style="font-size:11px">' + esc(e.source_system || e.kind) + '</td><td style="font-size:11px">' + esc(typeof summary === "string" ? summary : JSON.stringify(summary).slice(0, 60)) + '</td></tr>';
    }).join("") + '</tbody></table></div>' : "No captured elements") + (sourceVr ? renderSection("Source Record", renderKV("Verification Record", '<span class="link" onclick="openVRDetail(\'' + sourceVr.id + '\')">' + sourceVr.id + '</span>') + renderKV("Replayability", statusBadge(sourceVr.replayability)) + renderKV("Label", sourceVr.current_label_id ? '<span class="link">' + esc(sourceVr.current_label_id) + '</span>' : "—")) : "")) : "",
    activeTab === "replay" ? renderSection("Replay Execution Workspace", replayColumnsHtml) + (i.replay_result && i.replay_result.reason ? '<div class="error-state" style="margin-top:12px">Replay issue: ' + esc(i.replay_result.reason) + '</div>' : "") + renderSection("Decisions", renderKV("Original", '<span class="decision-pill decision-fail">' + esc(originalDecision) + '</span>') + renderKV("Replayed", '<span class="decision-pill ' + (replayedDecision === originalDecision ? "decision-fail" : "decision-neutral") + '">' + esc(replayedDecision || "Pending") + '</span>') + renderKV("Comparison", replayStatus === "pass" ? '<span style="color:var(--green);font-weight:800">Failure reproduced ✓</span>' : '<span style="color:var(--dim)">Pending</span>')) : "",
    activeTab === "fix" ? fixDetailHtml : "",
    activeTab === "proof" ? proofDetailHtml : "",
    activeTab === "gate" ? gateHtml : "",
    activeTab === "audit" ? renderSection("Chronological Audit Trail", custodyHtml || "No audit events recorded.") : "",
    '</div>',
    // Action bar
    '<div class="action-row" style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">',
    '<button class="btn' + (i.replay_result ? " btn-outline" : "") + '" onclick="runIncidentReplay(\'' + i.incident_id + '\')">' + (i.replay_result ? "Replay Again" : "Run Replay") + '</button>',
    (i.replay_result && !i.mutation_result ? '<button class="btn btn-amber" onclick="runIncidentVerify(\'' + i.incident_id + '\')">Verify Fix</button>' : ""),
    (!cert.certificate_id ? (wf.can_issue_proof ? '<button class="btn btn-green" onclick="confirmIssueProof(\'' + i.incident_id + '\')">Issue Proof</button>' : '<button class="btn btn-green" disabled title="' + esc(proofError || "Fix verification required first") + '">Issue Proof</button>') : ""),
    (sourceVr && cert.certificate_id ? '<button class="btn btn-sm btn-outline" onclick="promoteToScenario(\'' + sourceVr.id + '\', \'' + i.incident_id + '\')">Promote to Scenario</button>' : ""),
    '</div>',
  ].join("\n");
}

function switchIncidentTab(id) {
  S._incTab = id;
  openIncidentDetail(S.selectedIncident);
}

function wfAction(incidentId, label) {
  if (label.includes("Replay")) runIncidentReplay(incidentId);
  else if (label.includes("Fix")) runIncidentVerify(incidentId);
  else if (label.includes("Proof")) runIncidentCertify(incidentId);
}

async function runIncidentReplay(id) {
  try {
    const result = await apiPost("/v1/incidents/" + id + "/replay");
    notify("Replay completed", "success");
    const runId = result.replay_run_id;
    if (runId) {
      const started = Date.now();
      const notified = {};
      const poll = setInterval(async () => {
        try {
          const events = await apiGet("/v1/replay-runs/" + encodeURIComponent(runId) + "/events");
          events.forEach(function(ev) {
            const key = ev.sequence + "-" + ev.step;
            if (!notified[key] && ev.status !== "running") {
              notified[key] = true;
              notify("Replay: " + ev.step + " → " + ev.status, ev.status === "error" || ev.status === "escalation_required" ? "error" : "info");
            }
          });
          const terminal = ["pass","fail","reproduced","error","escalation_required","diverged"];
          const done = events.length > 0 && events.every(function(ev) { return terminal.includes(ev.status); });
          if (done || Date.now() - started > 15000) clearInterval(poll);
        } catch (_) {}
      }, 500);
      setTimeout(function() { clearInterval(poll); }, 15000);
    }
    openIncidentDetail(id);
  } catch (e) {
    notify("Replay failed: " + e.message, "error");
  }
}

async function runIncidentVerify(id) {
  try {
    await apiPost("/v1/incidents/" + id + "/mutation-tests", {fix_config: {threshold: 620}});
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
    const reason = String(e.message || "unknown error").replace(/^\d+\s+[^—]+—\s*/, "");
    notify("Proof issue failed: " + reason, "error");
    openIncidentDetail(id);
  }
}

function selectReplayEvent(idx) {
  S._selectedReplayIdx = idx;
  openIncidentDetail(S.selectedIncident);
}

function confirmIssueProof(incidentId) {
  renderDrawer("Issue Proof of Mitigation", [
    '<div class="section-title">Proposed Claim</div>',
    '<p style="font-size:12px;color:var(--muted);margin-bottom:12px">This proof certifies the fix for this specific scenario under the recorded conditions. It does <strong>not</strong> certify general AI safety, fairness, regulatory compliance, or performance.</p>',
    '<div class="proof-pending" style="border:1px solid var(--amber);padding:12px;border-radius:8px;margin-bottom:12px">',
    '<strong style="color:var(--amber)">Explicit scope boundaries</strong>',
    '<ul style="font-size:12px;color:var(--muted);margin:8px 0 0 16px">',
    '<li>This proof applies only to the tested scenario and recorded conditions.</li>',
    '<li>No claim is made about general AI safety, fairness, or regulatory compliance.</li>',
    '<li>No claim is made about the AI system\'s performance on untested inputs.</li>',
    '<li>The proof is bounded by the cassette evidence, replay method, and fix configuration used during verification.</li>',
    '</ul></div>',
    '<div class="action-row" style="margin-top:16px">',
    '<button class="btn btn-green" onclick="runIncidentCertify(\'' + incidentId + '\')">Confirm & Issue Proof</button>',
    '<button class="btn btn-outline" onclick="closeDrawer()">Cancel</button>',
    '</div>',
  ].join("\n"));
}

async function promoteToScenario(vrId, incidentId) {
  try {
    const r = await apiPost("/v1/scenarios?vr_id=" + encodeURIComponent(vrId));
    notify("Promoted to scenario: " + r.id, "success");
    openIncidentDetail(incidentId);
  } catch (e) {
    notify("Promotion failed: " + e.message, "error");
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
            <button class="btn btn-sm btn-outline" onclick="downloadProofBlob('${p.incident_id}', '${p.proof_id}', 'json')">JSON</button>
            <button class="btn btn-sm btn-outline" onclick="downloadProofBlob('${p.incident_id}', '${p.proof_id}', 'pdf')">PDF</button>
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
  const cert = p.certificate || {};
  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('proofs')">← Back to Proofs</button>
    ${badgeDemo()}
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      ${statusBadge("certified")}
      <span style="font-size:13px;color:var(--muted)">ID: ${p.proof_id}</span>
    </div>
    <div class="proof-bundle">
      <h3>${p.proof_id}</h3>
      ${renderKV("Decision Workflow", p.workflow_title || cert.workflow_title || "Recorded AI decision workflow")}
      ${renderKV("Source Incident", `<span class="link" onclick="openIncidentDetail('${p.incident_id}')">${p.incident_id}</span>`)}
      ${renderKV("Source Verification Record", p.verification_record_id ? `<span class="link" onclick="openVRDetail('${p.verification_record_id}')">${p.verification_record_id}</span>` : "—")}
      ${renderKV("Source System", p.source_system_id || "—")}
      ${renderKV("Original AI Decision", `<span class="decision-pill decision-fail">${esc(p.original_decision || "—")}</span>`)}
      ${renderKV("Verified Fixed Outcome", `<span class="decision-pill decision-pass">${esc(p.mutated_decision || cert.mutated_decision || "—")}</span>`)}
      ${renderKV("Expected Outcome Provenance", cert.expected_correct_behavior || "UNDERWRITING_REVIEW")}
      ${renderKV("Replay Method", cert.replay_method || "sealed cassette replay")}
      ${renderKV("Root Hash / Seal", cert.root_hash || "—")}
      ${renderKV("Signature Status", sig === true ? "✓ Valid" : sig === false ? "✗ Invalid" : "Unknown")}
      ${renderKV("Signing Algorithm", cert.signing_algorithm || "—")}
      ${renderKV("Claim Scope", p.claim_scope || "Verified fix for this tested scenario under recorded conditions. Does not certify general AI safety.")}
      ${renderKV("Limitations", p.known_limitations || cert.known_limitations || "Not documented")}
      <div class="action-row" style="margin-top:12px">
        <button class="btn btn-sm btn-outline" onclick="downloadProofBlob('${p.incident_id}', '${p.proof_id}', 'json')">Download JSON</button>
        <button class="btn btn-sm btn-outline" onclick="downloadProofBlob('${p.incident_id}', '${p.proof_id}', 'pdf')">Download PDF</button>
        <button class="btn btn-sm btn-outline" onclick="verifyProofSig('${p.incident_id}', '${p.proof_id}')">Verify Signature</button>
      </div>
      <div class="proof-pending" style="margin-top:16px">
        <strong>Bounded claim</strong>
        <p>This proof verifies that the fix produces the expected outcome for this recorded scenario. It does not certify that the AI system is safe in general, unbiased, free of hallucination, or compliant with all regulations.</p>
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
    ${renderSection("Active Scenarios", scenarios.length ? scenarios.map(s => scenarioCard(s)).join("") : `<div class="empty-state compact"><h3>No scenarios in the library yet</h3><p>Promote a verified incident from the incident detail view, or seed demo data.</p></div>`)}
    ${renderSection("Scenario Candidates", candidates.length ? candidates.filter(sc => sc.state === "candidate").map(sc => candidateCard(sc)).join("") : `<div class="empty-state compact"><h3>No candidates ready</h3><p>Candidates are created when you promote an incident that meets the readiness criteria.</p></div>`)}
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
    if (scenarioIds.length === 1) {
      const r = await apiPost("/v1/scenarios/" + encodeURIComponent(scenarioIds[0]) + "/execute?agent_version=" + encodeURIComponent(S.agentVersion));
      notify(`Scenario run ${r.status}: ${(r.summary || {}).passed || 0} passed, ${(r.summary || {}).failed || 0} failed, ${(r.summary || {}).errored || 0} errored`, "success");
    } else {
      const r = await apiPost("/v1/scenario-runs", {scenario_ids: scenarioIds, agent_version: S.agentVersion});
      notify(`Scenario run ${r.status}: ${(r.summary || {}).passed || 0} passed, ${(r.summary || {}).failed || 0} failed, ${(r.summary || {}).errored || 0} errored`, "success");
    }
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
    `).join("") : `<div class="empty-state compact"><h3>No readiness policies</h3><p>Create one from the Scenario detail view or use the button below.</p></div>`}
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
    ` : `<div class="empty-state compact"><h3>No readiness checks yet</h3><p>Run a readiness check on a policy to see results here.</p></div>`)}
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
    notify("Readiness check " + r.verdict, r.verdict === "passed" ? "success" : r.verdict === "fail" ? "warn" : "error");
    S.selectedReadinessCheck = r.id;
    nav("readiness-detail");
  } catch (e) {
    notify("Readiness check failed: " + e.message, "error");
  }
}

async function triggerReleaseGate(policyId, agentVersion) {
  try {
    const r = await apiPost("/v1/release-gate/checks", {policy_id: policyId, agent_version: agentVersion});
    notify("Release gate " + r.status, r.status === "pass" ? "success" : r.status === "fail" ? "warn" : "error");
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
      ${renderKV("Scenario Run", gate.scenario_run_id || "—")}
      ${renderKV("Certificate", gate.certificate_id || "—")}
      ${renderKV("Error Code", gate.error_code || "—")}
      ${renderKV("Retry Guidance", gate.retry_guidance || "—")}
    `)}
    ${gate.scenario_results && gate.scenario_results.length ? renderSection("Scenario Results", `
      ${renderTable(["Scenario", "Expected", "Actual", "Status", "Reason"], gate.scenario_results.map(r => [
        esc(r.scenario_id),
        esc(r.expected_decision || "—"),
        esc(r.actual_decision || "—"),
        statusBadge(r.status),
        esc(r.reason || "—"),
      ]))}
    `) : ""}
    ${gate.evidence_refs && gate.evidence_refs.length ? renderSection("Evidence References", `
      <div class="evidence-list">${gate.evidence_refs.map(ref => `<code>${esc(ref)}</code>`).join("")}</div>
    `) : ""}
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
      <div id="settings-org-info">${sk(60)}</div>
    `)}
    ${renderSection("Integrations", `
      <div class="action-row">
        ${renderDisabledAction("GRC Connector", "Planned")}
        ${renderDisabledAction("CI/CD release pipeline integration", "Planned")}
      </div>
    `)}
    ${renderSection("Users & Roles", `
      <p style="font-size:12px;color:var(--muted)">Users and roles are planned for the compliance release.</p>
    `)}
  `;
  loadApiKeys();
  try {
    const org = await apiGet("/v1/platform/org");
    q("#settings-org-info").innerHTML = renderKV("Name", esc(org.name || "")) + renderKV("ID", esc(org.id || ""));
  } catch (e) {
    q("#settings-org-info").innerHTML = `<p style="color:var(--red);font-size:12px">Failed to load org info.</p>`;
  }
}

// --- ABOUT ---

function renderAbout(c) {
  c.innerHTML = `
    <div class="int-card" style="margin-bottom:20px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><h2>About Notary Platform</h2></div>
        <span class="badge badge-built">v0.1.0</span>
      </div>
      <p style="font-size:13px;color:var(--muted);margin-top:8px">Notary is an AI decision assurance platform. It captures, seals, replays, and verifies AI decisions to produce replayable evidence for compliance and release gates.</p>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
      <div class="int-card">
        <h4>Capabilities</h4>
        <ul style="font-size:12px;line-height:1.8;padding-left:16px">
          <li><strong>Capture</strong> — Seal AI decision context as a tamper-evident snapshot</li>
          <li><strong>Replay</strong> — Reconstruct the decision using cassette-based deterministic replay</li>
          <li><strong>Verify Fix</strong> — Mutate agent logic and confirm the fix changes the outcome</li>
          <li><strong>Certify</strong> — Issue scenario-scoped cryptographic proof of mitigated failure</li>
          <li><strong>Release Gate</strong> — Block releases when known failure scenarios reappear</li>
        </ul>
      </div>
      <div class="int-card">
        <h4>Architecture</h4>
        <ul style="font-size:12px;line-height:1.8;padding-left:16px">
          <li><strong>Sealed Snapshots</strong> — Evidence graph with deterministic root hash</li>
          <li><strong>Response Cassette</strong> — Recorded tool/API responses for offline replay</li>
          <li><strong>Scenario Library</strong> — Reusable failure scenarios for release gates</li>
          <li><strong>Proof Bundles</strong> — Signed claims with chain-of-custody events</li>
          <li><strong>Evidence Pipeline</strong> — Capture → Label → Replay → Fix → Certify</li>
        </ul>
      </div>
    </div>
    <div class="int-card">
      <h4>API Endpoints</h4>
      <div style="font-size:12px;margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:4px">
        <div><span class="mono">POST /v1/verification-records/from-snapshot</span></div>
        <div style="color:var(--muted)">Create a VR from a captured snapshot</div>
        <div><span class="mono">POST /v1/incidents/{id}/replay</span></div>
        <div style="color:var(--muted)">Run deterministic replay</div>
        <div><span class="mono">POST /v1/incidents/{id}/mutation-tests</span></div>
        <div style="color:var(--muted)">Verify fix via mutation testing</div>
        <div><span class="mono">POST /v1/incidents/{id}/certificates</span></div>
        <div style="color:var(--muted)">Issue proof certificate</div>
        <div><span class="mono">POST /v1/scenarios/{id}/execute</span></div>
        <div style="color:var(--muted)">Execute a scenario run</div>
        <div><span class="mono">GET /v1/platform/home</span></div>
        <div style="color:var(--muted)">Dashboard health data</div>
      </div>
      <p style="font-size:11px;color:var(--dim);margin-top:12px">Full API reference: <span class="link" onclick="fetch('/v1/openapi.json').then(r=>r.json()).then(s=>renderDrawer('OpenAPI Spec',renderCodeBlock(JSON.stringify(s,null,2))))">/v1/openapi.json</span></p>
    </div>
  `;
}

// --- EVIDENCE ---

function renderEvidence(c, vrs) {
  const artifacts = [];
  vrs.forEach(v => {
    if (v.root_hash) artifacts.push({ type: "Verification Record", id: v.id, hash: v.root_hash, created: v.created_at, source: v.source_system_id || v.agent_id || "—" });
    (v.events || []).forEach(e => {
      if (e.kind === "input" || e.kind === "tool_call" || e.kind === "decision") {
        artifacts.push({ type: "Event: " + e.kind, id: v.id + "/" + (e.id || e.kind), hash: "—", created: e.timestamp || v.created_at, source: e.source_system || "—" });
      }
    });
  });
  if (!artifacts.length) {
    c.innerHTML = renderEmptyState("No Evidence", "Evidence artifacts appear when Verification Records are created.",
      '<button class="btn" onclick="nav(\'setup\')">Go to Setup</button>');
    return;
  }
  c.innerHTML = `
    <div class="int-card" style="margin-bottom:16px">
      <p style="font-size:12px;color:var(--muted)">Evidence artifacts from captured Verification Records. Each root hash seals a chain of custody events.</p>
    </div>
    <div class="table-wrap">
      <table class="np-table">
        <thead><tr><th>Type</th><th>ID</th><th>Root Hash</th><th>Created</th><th>Source</th></tr></thead>
        <tbody>${artifacts.map(a => `
          <tr>
            <td><span class="badge badge-built">${esc(a.type)}</span></td>
            <td style="font-family:mono;font-size:11px">${esc(a.id)}</td>
            <td style="font-family:mono;font-size:11px">${esc(a.hash)}</td>
            <td style="font-size:11px;color:var(--muted)">${esc(a.created)}</td>
            <td style="font-size:11px">${esc(a.source)}</td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
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
      ${renderCodeBlock(r.key, {mask: true})}
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
