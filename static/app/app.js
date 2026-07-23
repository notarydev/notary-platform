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
  setupWorkflowTemplates: null,
  setupSystems: null,
  setupCaptureMethod: null,
  setupEvidenceSources: null,
  setupPlanId: null,
  discoveryPlanId: null,
  discoveryRecords: [],
  discoveryFindings: [],
  discoveryMapping: {},
  discoveryCommitted: false,
  onbSystems: [],
  onbReceived: null,
  onbSending: false,
  demo: { step: 0 },
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
  if (res.status === 401) {
    S.authConfigured = true;
    throw new Error("Authentication required. Enter your API token in Settings.");
  }
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
  // Keep the old Discovery shortcut pointed at the canonical Setup plan.
  if (view === "discovery") {
    S.view = "setup";
    S.setupStep = SETUP_STEPS.findIndex((step) => step.id === "discovery");
  } else {
    S.view = view;
  }
  S.viewParams = {};
  if (query) {
    const params = new URLSearchParams(query);
    params.forEach((value, key) => { S.viewParams[key] = value; });
  }
  qa(".nav-item[data-view]").forEach((x) => x.classList.remove("active"));
  const b = q(`.nav-item[data-view="${S.view}"]`);
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
    } else if (S.view === "demo") {
      renderDemo(c);
    } else if (S.view === "integrations") {
      await renderIntegrations(c);
    } else if (S.view === "setup") {
      renderSetup(c);
    } else if (S.view === "discovery") {
      await renderDiscovery(c);
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
    if (S.authConfigured) {
      renderAuthPanel();
    } else {
      c.innerHTML = renderErrorState(e.message, "R()");
    }
  }
}

  function viewTitle(v) {
  const titles = {
    home: "Home",
    demo: "Demo",
    integrations: "Integrations",
    setup: "Setup",
    discovery: "Decision Discovery",
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

const DEMO_ORG_NAME = "Northstar Air";
function friendlyOrg(orgId, isDemo) {
  if (!orgId) return "Organization";
  if (isDemo) return DEMO_ORG_NAME;
  return "Notary Platform";
}

function renderHome(c, h) {
  q("#org-name").textContent = friendlyOrg(h.org_id, h.is_demo);
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
    ${h.is_demo ? renderHarborlineJourney() : ""}
    ${h.is_demo ? `<div style="margin-bottom:16px;font-size:12px;color:var(--amber);font-weight:600">${badgeDemo()} Fictional demo data — no production or customer data.</div>` : `<div style="margin-bottom:16px;font-size:12px;color:var(--green);font-weight:600">Production environment — live data.</div>`}
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
    { name: "Capture", detail: "Sealed Meridian loan decision", data: [
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
        <div class="eyebrow">Northstar Air · AI Support Bot Assurance</div>
        <h2>From AI failure to release gate</h2>
        <p>A support bot told a grieving customer they could get a retroactive bereavement refund — the airline's policy says the opposite. Notary captures the decision, replays it from sealed evidence, verifies the fix, and turns the failure into a release gate so the next bot release cannot repeat it.</p>
        <div class="golden-outcomes">
          <div class="golden-outcome"><span class="go-label">Original decision</span><span class="go-val" style="color:var(--red)">OFFER REFUND</span></div>
          <div class="golden-outcome"><span class="go-label">Expected outcome</span><span class="go-val" style="color:var(--green)">ESCALATE</span></div>
          <div class="golden-outcome"><span class="go-label">Gate before fix</span><span class="go-val" style="color:var(--red)">FAIL</span></div>
          <div class="golden-outcome"><span class="go-label">Gate after fix</span><span class="go-val" style="color:var(--green)">PASS</span></div>
        </div>
        <div class="action-row">
          <button class="btn btn-green" onclick="nav('demo')" data-testid="home-watch-demo-btn">&#9656; Watch the full demo</button>
          <button class="btn btn-outline" onclick="nav('setup')">Connect your systems</button>
        </div>
      </div>
      <div class="golden-panel">
        <div class="golden-panel-top">
          <span>${seeded ? "Seeded" : "The assurance loop"}</span>
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
    notify("Demo path ready: gate " + r.release_gate_before_fix_status + " -> " + r.release_gate_after_fix_status, "success");
    R();
  } catch (e) {
    notify("Demo seed failed: " + e.message, "error");
  }
}

function openReleaseGateDetail(id) {
  S.selectedReleaseGate = id;
  nav("release-gate-detail");
}

// --- SETUP ---

function setupCanNext(step) {
  const id = SETUP_STEPS[step] && SETUP_STEPS[step].id;
  if (id === "objective") return !!S.setupWorkflow;
  if (id === "workflow") return !!S.setupWorkflow;
  if (id === "ai-system") return !!S.setupAiSystem;
  if (id === "evidence") { const s = S.setupEvidenceSources; return s && s.some(x => x.selected); }
  if (id === "capture") return !!S.setupCaptureMethod;
  if (id === "selection-rules") return true;
  if (id === "discovery") return S.discoveryCommitted || !!S.onbReceived;
  if (id === "send" || id === "replay") { const v = S.onbReceived || S.discoveryCommitted; return !!v; }
  if (id === "readiness") return true;
  return true;
}

async function continueFromStep(step) {
  const id = SETUP_STEPS[step] && SETUP_STEPS[step].id;
  if (id === "objective" && S.setupWorkflow && S.setupWorkflow.workflow_type) {
    const name = q("#objective-name") ? q("#objective-name").value.trim() : S.setupWorkflow.name;
    if (name && S.setupPlanId) {
      try {
        await apiPatch("/v1/setup/plans/" + S.setupPlanId, {
          workflow_type: S.setupWorkflow.workflow_type,
          workflow_name: name,
        });
        S.setupWorkflow.name = name;
      } catch (e) { /* non-blocking */ }
    }
  }
  if (id === "evidence") {
    await saveEvidenceSources();
  }
  if (id === "selection-rules") {
    await saveRecordSelectionRules();
  }
  if (id === "discovery" && !S.discoveryCommitted) {
    notify("Preview and commit at least one decision record before continuing", "error");
    return;
  }
  if (id === "capture" && S.setupCaptureMethod) {
    await saveCaptureMethod();
  }
  renderSetupStep(step + 1);
}

function toggleSetupSystem(id) {
  const s = S.setupSystems;
  if (!s) return;
  const sys = s.find(x => x.id === id);
  if (sys && sys.tier !== "excluded") {
    sys.selected = !sys.selected;
    renderSetupStep(S.setupStep || 0);
  }
}

function selectCaptureMethod(id) {
  S.setupCaptureMethod = id;
  renderSetupStep(S.setupStep || 0);
}

async function saveCaptureMethod() {
  const planId = S.setupPlanId;
  if (!planId || !S.setupCaptureMethod) return;
  try {
    await apiPut("/v1/setup/plans/" + planId + "/capture-method", { capture_method: S.setupCaptureMethod });
    notify("Capture method saved", "success");
  } catch (e) {
    notify("Failed to save capture method: " + e.message, "error");
  }
}

const SETUP_STEPS = [
  { id: "objective", label: "Define Objective", desc: "What AI decision are you assuring?" },
  { id: "workflow", label: "Configure Decision Workflow", desc: "Configure the decision workflow details" },
  { id: "ai-system", label: "Register AI System", desc: "The system making this decision" },
  { id: "evidence", label: "Decision Evidence Sources", desc: "What evidence explains the decision" },
  { id: "capture", label: "Choose Capture Method", desc: "How Notary receives records" },
  { id: "selection-rules", label: "Record Selection Rules", desc: "Which conversations become records" },
  { id: "discovery", label: "Discover Decision Records", desc: "Preview and select decisions worth proving" },
  { id: "send", label: "Send or Import Records", desc: "Create first Verification Records" },
  { id: "replay", label: "Review Replayability", desc: "Can it be deterministically replayed?" },
  { id: "readiness", label: "Readiness Assessment", desc: "Is everything ready for production?" },
];

const SETUP_WORKFLOW_TYPES = [
  { id: "refund_or_policy_answer", label: "Refund or Policy Answer", desc: "Should this customer get a refund or escalation?" },
  { id: "support_escalation", label: "Support Escalation", desc: "Should this chat escalate to a human?" },
  { id: "lending_decision", label: "Lending Decision", desc: "Approve, deny, or review this loan?" },
  { id: "insurance_claim_triage", label: "Insurance Claim Triage", desc: "Pay, deny, or escalate this claim?" },
  { id: "healthcare_prior_auth", label: "Healthcare Prior Auth", desc: "Approve or escalate this prior-auth?" },
  { id: "hiring_screening", label: "Hiring Screening", desc: "Advance this candidate to review?" },
  { id: "custom", label: "Custom Workflow", desc: "Define your own decision workflow" },
];

const SETUP_CAPTURE_METHODS = [
  {
    id: "sdk",
    title: "Python SDK",
    best: "Instrumented Python AI agents.",
    captures: "LLM calls, tool calls, decisions, and sealed cassettes in-process.",
    not: "Non-Python backends or third-party systems you cannot instrument.",
    action: "openSDKSetup()",
  },
  {
    id: "api",
    title: "API Submission",
    best: "Backend systems sending Verification Records directly.",
    captures: "Structured decision evidence, labels, and references.",
    not: "In-process model internals unless you serialize them.",
    action: "openAPISubmissionSetup()",
  },
  {
    id: "manual",
    title: "Manual Submission",
    best: "Complaints, overrides, disputes, or one-off reviews.",
    captures: "Human-provided expected outcome and evidence summary.",
    not: "High-volume automated decisions.",
    action: "openManualSubmissionForm()",
  },
  {
    id: "webhook",
    title: "Webhook",
    best: "Source-system event forwarding.",
    captures: "Events that represent a decision or escalation.",
    not: "Arbitrary operational telemetry.",
    action: "openWebhookSetup()",
  },
];

function renderSetupStepIndicator(step) {
  return `
    <div class="setup-steps">
      ${SETUP_STEPS.map((s, i) => `
        <div class="setup-step ${i === step ? 'active' : i < step ? 'done' : ''}">
          <span class="setup-step-num">${i + 1}</span>
          <span class="setup-step-label">${esc(s.label)}</span>
        </div>
        ${i < SETUP_STEPS.length - 1 ? '<span class="setup-step-line"></span>' : ''}
      `).join("")}
    </div>`;
}

function renderSetupNav(step) {
  const canNext = setupCanNext(step);
  const isLast = step === SETUP_STEPS.length - 1;
  const id = SETUP_STEPS[step] && SETUP_STEPS[step].id;
  return `
    <div class="setup-nav">
      ${step > 0 ? `<button class="btn btn-outline" onclick="renderSetupStep(${step - 1})" data-testid="setup-back-btn">Back</button>` : "<span></span>"}
      ${isLast
        ? `<button class="btn btn-green" onclick="nav('verification-records')" data-testid="setup-finish-btn">Finish — View Records</button>`
        : `<button class="btn" onclick="continueFromStep(${step})" ${canNext ? "" : "disabled"} data-testid="setup-next-btn">Continue</button>`}
    </div>`;
}

function renderSetupTrackerInner(step) {
  S.setupMaxStep = Math.max(S.setupMaxStep || 0, step);
  const items = SETUP_STEPS.map((s, i) => {
    const state = i === step ? "active" : i < step ? "done" : "";
    const clickable = i <= S.setupMaxStep;
    return `
      <button class="setup-tstep ${state}" ${clickable ? `onclick="renderSetupStep(${i})"` : "disabled"} data-testid="setup-step-${s.id}">
        <span class="setup-tnum">${i < step ? "&#10003;" : i + 1}</span>
        <span class="setup-tbody">
          <span class="setup-tlabel">${esc(s.label)}</span>
          <span class="setup-tdesc">${esc(s.desc)}</span>
        </span>
      </button>`;
  }).join("");
  const pct = Math.round((step / (SETUP_STEPS.length - 1)) * 100);
  return `
    <div class="setup-progress-label">Step ${step + 1} of ${SETUP_STEPS.length} · ${pct}% complete</div>
    <div class="setup-progress"><div class="setup-progress-bar" style="width:${pct}%"></div></div>
    <div class="setup-tsteps">${items}</div>
    <div class="setup-token">
      <div class="setup-token-top"><span>API Token</span><span class="badge badge-built">ACTIVE</span></div>
      ${renderCodeBlock(S.token || "ntry-demo-...", {mask: true})}
      <div style="font-size:11px;color:var(--muted);margin-top:8px">Sent automatically in headers. Manage in <span class="link" onclick="nav('settings')">Settings</span>.</div>
    </div>`;
}

async function renderSetupObjectiveStep() {
  const saved = S.setupWorkflow || {};
  const templates = await apiGet("/v1/setup/workflow-templates").catch(() => []);
  S.setupWorkflowTemplates = templates;
  return `
    <div class="setup-step-content">
      <h2>What AI decision do you want to assure?</h2>
      <p class="setup-lead">Pick a workflow template to define the decision type. Notary uses this to recommend evidence sources, capture methods, and record selection rules.</p>
      <div class="capture-grid">
        ${templates.map(t => `
          <div class="capture-card ${saved.workflow_type === t.id ? 'selected' : ''}" onclick="selectObjectiveTemplate('${t.id}')" style="cursor:pointer" data-testid="template-${t.id}">
            <h3>${esc(t.label || t.name)}</h3>
            <div style="font-size:13px;color:var(--text);margin-top:8px">${esc(t.description)}</div>
            ${saved.workflow_type === t.id ? `<span class="badge badge-built" style="margin-top:8px">Selected</span>` : ""}
          </div>
        `).join("")}
        ${templates.length === 0 ? SETUP_WORKFLOW_TYPES.map(t => `
          <div class="capture-card ${saved.workflow_type === t.id ? 'selected' : ''}" onclick="selectObjectiveTemplate('${t.id}')" style="cursor:pointer" data-testid="template-${t.id}">
            <h3>${esc(t.label)}</h3>
            <div style="font-size:13px;color:var(--text);margin-top:8px">${esc(t.desc)}</div>
            ${saved.workflow_type === t.id ? `<span class="badge badge-built" style="margin-top:8px">Selected</span>` : ""}
          </div>
        `).join("") : ""}
      </div>
      <div style="margin-top:20px">
        <div class="np-field"><label>Workflow name</label>
          <input id="objective-name" value="${esc(saved.name || "")}" placeholder="e.g. Bereavement Refund Policy Answer" style="width:100%">
        </div>
      </div>
      ${saved.workflow_type ? `<button class="btn" onclick="saveObjectiveStep()" data-testid="save-objective-btn">Save & Continue</button>` : ""}
    </div>`;
}

async function renderSetupWorkflowStep() {
  const saved = S.setupWorkflow || {};
  const planId = S.setupPlanId;
  let plan = {};
  if (planId) {
    plan = await apiGet("/v1/setup/plans/" + planId).catch(() => ({}));
  }
  return `
    <div class="setup-step-content">
      <h2>Configure decision workflow</h2>
      <p class="setup-lead">Refine the workflow for <strong>${esc(saved.name || plan.workflow_name || "")}</strong>. These details help Notary determine what evidence to capture.</p>
      <div class="np-form">
        <div class="np-field"><label>What decision does the AI make?</label>
          <textarea id="wf-description" rows="2" placeholder="e.g. The bot decides whether to offer a refund, escalate, or answer based on policy.">${esc(saved.description || plan.description || "")}</textarea>
        </div>
        <div class="np-field"><label>What can go wrong?</label>
          <textarea id="wf-failure" rows="2" placeholder="e.g. Bot gives a customer a refund policy that does not exist.">${esc(saved.common_failure || plan.common_failure || "")}</textarea>
        </div>
        <div class="np-field"><label>What should happen instead? (expected safe outcome)</label>
          <input id="wf-outcome" value="${esc(saved.expected_safe_outcome || plan.expected_safe_outcome || "")}" placeholder="e.g. ESCALATE_TO_HUMAN"></div>
        <div class="integ-form-row">
          <div class="np-field" style="flex:1"><label>Risk level</label>
            <select id="wf-risk">
              <option value="low" ${(saved.risk_level || plan.risk_level) === "low" ? "selected" : ""}>Low</option>
              <option value="medium" ${(!(saved.risk_level || plan.risk_level) || (saved.risk_level || plan.risk_level) === "medium") ? "selected" : ""}>Medium</option>
              <option value="high" ${(saved.risk_level || plan.risk_level) === "high" ? "selected" : ""}>High</option>
              <option value="critical" ${(saved.risk_level || plan.risk_level) === "critical" ? "selected" : ""}>Critical</option>
            </select>
          </div>
        </div>
        <button class="btn" onclick="saveWorkflowStep()" data-testid="save-workflow-btn">Save Workflow</button>
      </div>
    </div>`;
}

function loadWorkflow(id) {
  const wf = S.setupWorkflows.find(w => w.id === id);
  if (wf) { S.setupWorkflow = wf; renderSetupStep(0); }
}

async function selectObjectiveTemplate(templateId) {
  const templates = S.setupWorkflowTemplates || SETUP_WORKFLOW_TYPES;
  const t = templates.find(x => x.id === templateId);
  if (!S.setupWorkflow) S.setupWorkflow = {};
  S.setupWorkflow.workflow_type = templateId;
  if (t) S.setupWorkflow.name = t.label || t.name;
  if (S.setupPlanId) {
    try {
      const updated = await apiPatch("/v1/setup/plans/" + S.setupPlanId, {
        workflow_type: templateId,
        workflow_name: S.setupWorkflow.name,
      });
      S.setupWorkflow = { ...S.setupWorkflow, ...updated };
    } catch (e) { /* will retry on save */ }
  }
  renderSetupStep(S.setupStep);
}

async function saveObjectiveStep() {
  const name = q("#objective-name") ? q("#objective-name").value.trim() : (S.setupWorkflow && S.setupWorkflow.name);
  if (!name) { notify("Workflow name is required", "error"); return; }
  if (!S.setupWorkflow) S.setupWorkflow = {};
  S.setupWorkflow.name = name;
  try {
    if (S.setupPlanId) {
      const updated = await apiPatch("/v1/setup/plans/" + S.setupPlanId, {
        workflow_type: S.setupWorkflow.workflow_type,
        workflow_name: S.setupWorkflow.name,
      });
      S.setupWorkflow = { ...S.setupWorkflow, ...updated };
    }
    notify("Objective saved", "success");
    renderSetupStep(S.setupStep);
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function saveWorkflowStep() {
  const body = {
    description: q("#wf-description").value,
    common_failure: q("#wf-failure").value,
    expected_safe_outcome: q("#wf-outcome").value,
    risk_level: q("#wf-risk").value,
  };
  if (S.setupWorkflow && S.setupWorkflow.name) body.workflow_name = S.setupWorkflow.name;
  if (S.setupWorkflow && S.setupWorkflow.workflow_type) body.workflow_type = S.setupWorkflow.workflow_type;
  try {
    if (S.setupPlanId) {
      const result = await apiPatch("/v1/setup/plans/" + S.setupPlanId, body);
      S.setupWorkflow = { ...(S.setupWorkflow || {}), ...result };
      notify("Workflow saved", "success");
    } else {
      notify("No active plan", "error");
      return;
    }
    renderSetupStep(S.setupStep);
  } catch (e) {
    notify("Failed to save workflow: " + e.message, "error");
  }
}

async function renderEvidenceSourcesStep() {
  let planId = S.setupPlanId;
  if (!planId) {
    try {
      const plan = await apiPost("/v1/setup/plans", {});
      S.setupPlanId = plan.id;
      planId = plan.id;
    } catch (e) {
      return `<div class="setup-step-content"><h2>Define evidence boundary</h2><p class="setup-lead">Could not create setup plan. ${esc(e.message)}</p></div>`;
    }
  }
  const resp = await apiGet("/v1/setup/plans/" + planId + "/evidence-sources").catch(() => null);
  if (!resp) {
    return `<div class="setup-step-content"><h2>Define evidence boundary</h2><p class="setup-lead">Could not load evidence sources.</p></div>`;
  }
  const sources = [
    ...(resp.required || []).map(s => ({...s, id: s.field, name: s.label, why_include: s.why, required: true, selected: true, status: "required"})),
    ...(resp.optional || []).map(s => ({...s, id: s.field, name: s.label, why_include: s.why, required: false, selected: true, status: "selected"})),
  ];
  S.setupEvidenceSources = sources;
  const selected = sources.filter(s => s.selected).length;
  const total = sources.length;
  return `
    <div class="setup-step-content">
      <h2>What evidence does this decision depend on?</h2>
      <p class="setup-lead">Pick the sources that explain the AI decision. Notary seals decision evidence, not operational telemetry. ${S.setupWorkflow && S.setupWorkflow.name ? 'For workflow: <strong>' + esc(S.setupWorkflow.name) + '</strong>' : ''}</p>
      <div style="font-size:12px;color:var(--muted);margin-bottom:12px">${selected}/${total} sources selected</div>
          ${sources.map(s => `
            <div class="source-row" style="display:flex;align-items:flex-start;padding:12px;border:1px solid var(--border);border-radius:8px;margin-bottom:8px;background:${s.selected ? 'var(--bg-card)' : 'var(--bg-secondary)'}">
              <label class="np-checkbox" style="margin-right:12px;margin-top:2px">
                <input type="checkbox" ${s.selected ? 'checked' : ''} ${s.required ? 'disabled' : ''} onchange="toggleEvidenceSource('${s.id}')">
                <span class="np-checkmark"></span>
              </label>
              <div style="flex:1">
                <strong>${esc(s.name)}</strong>
                <div style="font-size:12px;color:var(--text);margin-top:4px">${esc(s.captures)}</div>
                <div style="font-size:11px;color:var(--muted);margin-top:4px">${esc(s.why_include)}</div>
                ${!s.required ? `<div style="font-size:11px;color:var(--muted);margin-top:2px">Does not capture: ${esc(s.does_not_capture)}</div>` : ''}
              </div>
              <span class="badge ${s.selected ? 'badge-built' : 'badge-neutral'}">${s.required ? 'Required' : s.selected ? 'Selected' : 'Optional'}</span>
            </div>
          `).join('')}
        </div>
        <div style="margin-top:16px;font-size:12px;color:var(--muted);padding:12px;border:1px dashed var(--border);border-radius:8px">
          <strong>Out of scope for AI Decision Assurance</strong>
          <div style="margin-top:4px">Queue wait time, Employee workload, Generic CRM activity, Notification delivery, SLA analytics, Generic process optimization.</div>
        </div>
      </div>
    </div>`;
}

async function toggleEvidenceSource(id) {
  S.setupEvidenceSources = (S.setupEvidenceSources || []).map(s =>
    s.id === id && !s.required ? {...s, selected: !s.selected, status: s.selected ? "suggested" : "selected"} : s
  );
  await renderSetupStep(S.setupStep);
}

async function saveEvidenceSources() {
  const planId = S.setupPlanId;
  if (!planId) return;
  try {
    const srcs = S.setupEvidenceSources || [];
    const body = {
      required: srcs.filter(s => s.required).map(s => ({field: s.field, label: s.label, selected: true})),
      optional: srcs.filter(s => !s.required && s.selected).map(s => ({field: s.field, label: s.label, selected: true})),
      excluded: srcs.filter(s => !s.selected).map(s => ({field: s.field, label: s.label, selected: false})),
    };
    await apiPut("/v1/setup/plans/" + planId + "/evidence-sources", body);
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

function toggleSetupSystem(id) {
  S.setupSystems = (S.setupSystems || []).map(s =>
    s.id === id && s.tier !== "excluded" ? {...s, selected: !s.selected} : s
  );
  renderSetupStep(3);
}

function captureToken() {
  return (S.onbSystems[0] && S.onbSystems[0].token) || S.token || "ntry-your-token";
}

function renderCaptureSnippet(method) {
  const tok = captureToken();
  const base = "https://api.getnotary.ai/v1";
  let code = "";
  if (method === "sdk") {
    code = `# 1. Install SDK (not yet on PyPI — clone from repo)
git clone https://github.com/notarydev/notary-platform.git
cd notary-platform
pip install -e packages/notary-sdk-py

# 2. Capture a decision
from notary_sdk import RunCapture

capture = RunCapture(
    secret_key=b"your-secret-key",
    api_url="https://api.getnotary.ai",
    api_token="${tok}",
)

capture.capture_human_action(
    source_record_ref="CASE-1234",
    domain="Support",
)

capture.capture_llm(
    prompt="Can I get a bereavement refund after booking?",
    response="Checking policy...",
    model="support-bot-v42",
    temperature=0.0,
    seed=12345,
)

capture.capture_tool(
    method="GET",
    url="/policy-service/bereavement",
    response={"retroactive_refund_allowed": False, "human_review_required": True},
    status=200,
)

capture.capture_decision(
    decision="OFFER_RETROACTIVE_REFUND",
    expected_correct_behavior="ESCALATE_TO_HUMAN",
)

snapshot = capture.finalize(
    agent_version="support-bot-v42",
    policy_version="bereavement-policy-v7",
)

result = snapshot.submit(
    source_system_id="salesforce-service-cloud",
    source_record_ref="CASE-1234",
    agent_id="bereavement-support-bot",
    business_function="Bereavement refund policy answer",
    expected_outcome="ESCALATE_TO_HUMAN",
)

print(result)`;
  } else if (method === "api") {
    code = `curl -X POST ${base}/verification-records/from-snapshot \\\n  -H "Authorization: Bearer ${tok}" \\\n  -H "Content-Type: application/json" \\\n  -d '{\n  "schema_version": 1,\n  "source_system_id": "my-backend",\n  "source_record_ref": "CASE-1234",\n  "business_function": "customer_support",\n  "expected_outcome": "RESOLVE",\n  "agent_id": "agent:support-bot",\n  "elements": [\n    {"kind": "input", "sequence": 0, "payload": {"text": "Can I get a refund?"}},\n    {"kind": "decision", "sequence": 1, "payload": {"decision": "OFFER_REFUND"}}\n  ]\n}'`;
  } else if (method === "webhook") {
    code = `POST ${base}/verification-records/webhook\nAuthorization: Bearer ${tok}\n\n{\n  "source_id": "TKT-1234",\n  "events": [{"kind": "decision", "payload": {"decision": "DENY"}}]\n}`;
  } else {
    code = `# Manual submission\nSubmit a decision directly from the Verification Records screen —\nbest for complaints, overrides, and one-off reviews.`;
  }
  return `<div class="onb-snippet">
    <div class="section-title" style="margin-top:22px">Your ${esc(method.toUpperCase())} snippet</div>
    <div class="section-sub">Pre-filled with ${S.onbSystems[0] ? "your first system's" : "your"} ingest token. Drop it into your app to start sending decisions.</div>
    ${renderCodeBlock(code)}
  </div>`;
}

async function renderSetupCaptureStep() {
  const planId = S.setupPlanId;
  let recommendations = [];
  if (planId) {
    recommendations = await apiGet("/v1/setup/plans/" + planId + "/capture-methods/recommend").catch(() => []);
  }
  const methods = recommendations.length ? recommendations : SETUP_CAPTURE_METHODS;
  return `
    <div class="setup-step-content">
      <h2>How will Notary receive decision records?</h2>
      <p class="setup-lead">Pick how decisions reach Notary. You'll get a copy-paste snippet pre-filled with your token and endpoint.</p>
      <div class="capture-grid">
        ${methods.map(m => `
          <div class="capture-card ${S.setupCaptureMethod === m.id ? 'selected' : ''}" onclick="selectCaptureMethod('${m.id}')" style="cursor:pointer" data-testid="capture-method-${m.id}">
            <h3>${esc(m.title || m.name)}</h3>
            <div class="capture-field"><span>Recommended for</span><span>${esc(m.best_for || m.best || "")}</span></div>
            <div class="capture-field"><span>Captures</span><span>${esc(m.captures || m.description || "")}</span></div>
            <div class="capture-field"><span>Limitations</span><span>${esc(m.limitations || m.not || "")}</span></div>
            ${S.setupCaptureMethod === m.id ? `<span class="badge badge-built" style="margin-top:8px">Selected</span>` : ""}
          </div>
        `).join("")}
      </div>
      ${S.setupCaptureMethod ? renderCaptureSnippet(S.setupCaptureMethod) : `<div class="section-sub" style="margin-top:16px">Select a capture method to see its install snippet.</div>`}
    </div>`;
}

let S_RSR_CACHE = null;

async function renderSetupSelectionRulesStep() {
  let planId = S.setupPlanId;
  if (!planId) {
    try {
      const plan = await apiPost("/v1/setup/plans", {});
      S.setupPlanId = plan.id;
      planId = plan.id;
    } catch (e) {
      return '<div class="setup-step-content"><h2>Record Selection Rules</h2><p class="setup-lead">Could not create setup plan: ' + esc(e.message) + '</p></div>';
    }
  }
  let rules = S_RSR_CACHE;
  if (!rules) {
    try {
      rules = await apiGet("/v1/setup/plans/" + planId + "/record-selection-rules");
      S_RSR_CACHE = rules;
    } catch (e) {
      return '<div class="setup-step-content"><h2>Record Selection Rules</h2><p class="setup-lead">Could not load rules: ' + esc(e.message) + '</p></div>';
    }
  }
  return `
    <div class="setup-step-content">
      <h2>Which conversations become records?</h2>
      <p class="setup-lead">Choose what triggers a Verification Record to be created. Rules run against every conversation and generate sealed evidence only for matching events.</p>
      ${rules.map((r, i) => `
        <div class="rule-row" style="display:flex;align-items:center;padding:12px;border:1px solid var(--border);border-radius:8px;margin-bottom:8px;background:${r.enabled ? 'var(--bg-card)' : 'var(--bg-secondary)'}">
          <label class="np-checkbox" style="margin-right:12px">
            <input type="checkbox" ${r.enabled ? 'checked' : ''} onchange="toggleRecordSelectionRule('${r.id}', this.checked)">
            <span class="np-checkmark"></span>
          </label>
          <div style="flex:1">
            <strong>${esc(r.label)}</strong>
            <div style="font-size:12px;color:var(--muted)">${esc(r.description)}</div>
          </div>
          <span class="badge ${r.enabled ? 'badge-built' : 'badge-neutral'}">${r.enabled ? 'Active' : 'Disabled'}</span>
        </div>
      `).join('')}
      <div style="margin-top:16px;font-size:12px;color:var(--muted)">
        All matching rules are retained; the first matching rule supplies the primary trigger_type on the record.
        Rules are evaluated by Notary Platform for imports and submitted records. SDKs may apply lightweight local filtering, but the platform is the source of truth.
      </div>
    </div>`;
}

function toggleRecordSelectionRule(ruleId, enabled) {
  if (!S_RSR_CACHE) return;
  const r = S_RSR_CACHE.find(x => x.id === ruleId);
  if (r) { r.enabled = enabled; }
}

async function saveRecordSelectionRules() {
  const planId = S.setupPlanId;
  if (!planId || !S_RSR_CACHE) return;
  try {
    await apiPut("/v1/setup/plans/" + planId + "/record-selection-rules", S_RSR_CACHE);
    notify("Record selection rules saved", "success");
  } catch (e) {
    notify("Failed to save: " + e.message, "error");
  }
}

async function renderOnbRegisterStep() {
  const saved = S.setupAiSystem || {};
  const existing = await apiGet("/v1/setup/ai-systems").catch(() => []);
  S.setupAiSystems = existing;
  const wf = S.setupWorkflow;
  return `
    <div class="setup-step-content">
      <h2>Register the AI system making this decision</h2>
      <p class="setup-lead">${wf ? `For workflow <strong>${esc(wf.name)}</strong>, register the AI system that makes or recommends the decision.` : "The AI system is what makes or recommends the decision Notary assures."}</p>
      <div class="onb-register-grid">
        <div class="ic-form-card">
          <div class="np-form">
            <div class="np-field"><label>System name *</label><input id="ais-name" value="${esc(saved.name || "")}" placeholder="e.g. Bereavement Support Bot"></div>
            <div class="integ-form-row">
              <div class="np-field" style="flex:1"><label>System type</label>
                <select id="ais-type">
                  <option value="ai_agent" ${saved.system_type === "ai_agent" ? "selected" : ""}>AI Agent — Makes decisions and calls tools independently</option>
                  <option value="ai_enabled_app" ${saved.system_type === "ai_enabled_app" ? "selected" : ""}>AI-Enabled App — Business app with embedded AI</option>
                  <option value="decision_engine" ${saved.system_type === "decision_engine" ? "selected" : ""}>Decision Engine — Rules/model service returning decisions</option>
                  <option value="model_service" ${saved.system_type === "model_service" ? "selected" : ""}>Model Service — Model endpoint used by another system</option>
                </select>
              </div>
              <div class="np-field" style="flex:1"><label>Current version</label>
                <input id="ais-version" value="${esc(saved.deployment_version || "")}" placeholder="e.g. v42"></div>
            </div>
            <div class="integ-form-row">
              <div class="np-field" style="flex:1"><label>Risk classification</label>
                <select id="ais-risk">
                  <option value="" ${!saved.risk_classification ? "selected" : ""}>— Select —</option>
                  <option value="low" ${saved.risk_classification === "low" ? "selected" : ""}>Low</option>
                  <option value="medium" ${saved.risk_classification === "medium" ? "selected" : ""}>Medium</option>
                  <option value="high" ${saved.risk_classification === "high" ? "selected" : ""}>High</option>
                  <option value="critical" ${saved.risk_classification === "critical" ? "selected" : ""}>Critical</option>
                </select>
              </div>
              <div class="np-field" style="flex:1"><label>Business owner</label>
                <input id="ais-owner" value="${esc(saved.business_owner || "")}" placeholder="e.g. support-team@"></div>
            </div>
            <button class="btn" onclick="saveAiSystemStep()">${saved.id ? "Update System" : "Register System"}</button>
          </div>
        </div>
        <div class="onb-systems">
          <div class="section-title" style="margin-top:0">Registered AI systems (${existing.length})</div>
          ${existing.length ? existing.map(s => `
            <div class="onb-system-row">
              <div style="min-width:0">
                <strong>${esc(s.name)}</strong>
                <div class="onb-system-meta">${esc(s.system_type)} · ${esc(s.deployment_version || "no version")} · ${s.status}</div>
              </div>
              <button class="btn btn-sm btn-outline" onclick="loadAiSystem('${s.id}')">Edit</button>
            </div>`).join("") : `<div class="empty-state compact"><p>No AI systems yet. Register the system that makes the decision.</p></div>`}
        </div>
      </div>
    </div>`;
}

function loadAiSystem(id) {
  const s = S.setupAiSystems.find(a => a.id === id);
  if (s) { S.setupAiSystem = s; renderSetupStep(2); }
}

async function saveAiSystemStep() {
  const name = q("#ais-name").value.trim();
  if (!name) { notify("System name is required", "error"); return; }
  const body = {
    name,
    system_type: q("#ais-type").value,
    deployment_version: q("#ais-version").value,
    risk_classification: q("#ais-risk").value,
    business_owner: q("#ais-owner").value,
    environment_id: S.env,
  };
  const existing = S.setupAiSystem;
  try {
    let result;
    if (existing && existing.id) {
      result = await apiPut("/v1/setup/ai-systems/" + existing.id, body);
    } else {
      result = await apiPost("/v1/setup/ai-systems", body);
    }
    S.setupAiSystem = result;
    if (S.setupPlanId) {
      await apiPatch("/v1/setup/plans/" + S.setupPlanId, { ai_system_id: result.id });
    }
    notify("AI system registered", "success");
    renderSetupStep(S.setupStep);
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function renderOnbSendStep() {
  const wf = S.setupWorkflow;
  const ais = S.setupAiSystem;
  const rec = S.onbReceived;
  const sending = S.onbSending;
  const importMode = S.setupCaptureMethod === "import";
  const vrs = await apiGet("/v1/verification-records").catch(() => []);
  const hasVrs = vrs.length > 0 && vrs.some(v => v.source_type !== "demo_seed");
  if (rec || hasVrs) {
    const latest = rec || vrs[vrs.length - 1];
    return `
      <div class="setup-step-content">
        <h2>First records received</h2>
        <p class="setup-lead">Notary sealed your decision${latest.id ? " as " + esc(latest.id) : ""}. ${vrs.length} total record${vrs.length !== 1 ? "s" : ""}.</p>
        <div class="onb-received">
          <div class="onb-received-head"><span class="onb-live-dot ok"></span> Record received</div>
          <div class="packet-grid">
            <div class="packet-field"><span>Record ID</span><span class="mono">${esc(latest.id || "—")}</span></div>
            <div class="packet-field"><span>Replayability</span><span>${esc(latest.replayability || "pending")}</span></div>
            <div class="packet-field"><span>Records total</span><span>${vrs.length}</span></div>
          </div>
        </div>
      </div>`;
  }
  if (importMode) {
    return '<div class="setup-step-content">' +
      '<h2>Import records from export files</h2>' +
      '<p class="setup-lead">Upload a JSON or JSONL export from Zendesk, Salesforce, ServiceNow, Intercom, or any JSON decision-log export.</p>' +
      '<div class="np-form">' +
      '<div class="np-field"><label>Source system / export type</label>' +
      '<select id="import-source-type">' +
      '<option value="zendesk_export">Zendesk ticket export</option>' +
      '<option value="salesforce_export">Salesforce Service Cloud export</option>' +
      '<option value="servicenow_export">ServiceNow case export</option>' +
      '<option value="intercom_export">Intercom conversation export</option>' +
      '<option value="jsonl_export">JSONL decision log</option>' +
      '<option value="csv_export">CSV export</option>' +
      '</select></div>' +
      '<div class="np-field"><label>Paste JSON records (array of record objects)</label>' +
      '<textarea id="import-json" rows="8" placeholder=\'[{"source_record_ref":"TKT-123","business_function":"customer_support","elements":[{"kind":"input","payload":{"text":"Can I get a refund?"}},{"kind":"decision","payload":{"decision":"OFFER_REFUND"}}]}]\'></textarea>' +
      '</div>' +
      '<button class="btn" onclick="previewThenImport()">Preview & Import</button>' +
      '<div id="import-preview-results" style="margin-top:12px"></div>' +
      '</div>' +
      '<div style="margin-top:16px;font-size:12px;color:var(--muted)">Field mapping: source_record_ref, business_function, expected_outcome, agent_id, and elements are auto-mapped.</div>' +
      '</div>';
  }
  return '<div class="setup-step-content">' +
    '<h2>Send or import your first Verification Records</h2>' +
    '<p class="setup-lead">' + (ais ? "Run your instrumented " + esc(ais.name) : "Run your instrumented app") + ' or send a test record below.</p>' +
    '<div style="margin-bottom:16px">' +
    '<button class="btn btn-outline" onclick="sendTestCapture()" ' + (sending ? 'disabled' : '') + '>Send test record</button>' +
    '<span style="margin-left:8px;font-size:12px;color:var(--muted)">Creates a sample Verification Record</span>' +
    '</div>' +
    '<div style="font-size:12px;color:var(--muted)">Records appear here automatically. Go to Verification Records to view all records.</div>' +
    '<div class="onb-waiting ' + (sending ? 'active' : '') + '">' +
    '<div class="onb-radar"><span></span><span></span><span></span></div>' +
    '<div class="onb-live"><span class="onb-live-dot ' + (sending ? '' : 'idle') + '"></span> ' + (sending ? "Receiving record..." : "Waiting for your first verification record...") + '</div>' +
    '<button class="btn" onclick="sendTestCapture()" ' + (sending ? 'disabled' : '') + '>' + (sending ? 'Sending...' : 'Send test record') + '</button>' +
    '</div></div>';
}

async function sendTestCapture() {
  if (S.onbSending) return;
  S.onbSending = true;
  renderSetupStep(7);
  try {
    const snapshot = {
      schema_version: 1,
      source_system_id: "setup-wizard",
      source_record_ref: "SETUP-TEST-" + Date.now(),
      business_function: S.setupWorkflow ? S.setupWorkflow.id : "setup-test",
      elements: [
        {kind: "input", sequence: 0, payload: {text: "Can I get a bereavement refund after booking?"}},
        {kind: "tool", sequence: 1, payload: {method: "GET", url: "/policy/bereavement", response: {retroactive_refund_allowed: false}}},
        {kind: "decision", sequence: 2, payload: {decision: "OFFER_REFUND"}},
      ],
    };
    const r = await apiPost("/v1/verification-records/from-snapshot", snapshot);
    S.onbReceived = r;
    notify("Test record created: " + r.id, "success");
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
  S.onbSending = false;
  renderSetupStep(7);
}

async function importRecords() {
  const raw = q("#import-json") ? q("#import-json").value.trim() : "";
  if (!raw) { notify("Paste JSON records first", "error"); return; }
  const planId = S.setupPlanId;
  if (!planId) { notify("No active plan", "error"); return; }
  try {
    const records = JSON.parse(raw);
    const arr = Array.isArray(records) ? records : [records];
    const mapping = S.setupFieldMapping || {};
    const result = await apiPost("/v1/setup/plans/" + planId + "/imports/commit", { records: arr, field_mapping: mapping });
    notify("Imported " + (result.imported || result.count || 0) + " records", "success");
    if (result.records && result.records.length) {
      S.onbReceived = result.records[result.records.length - 1];
    } else {
      S.onbReceived = { id: "imported", replayability: "pending" };
    }
    renderSetupStep(8);
  } catch (e) {
    notify("Import failed: " + e.message, "error");
  }
}

async function previewThenImport() {
  const raw = q("#import-json") ? q("#import-json").value.trim() : "";
  if (!raw) { notify("Paste JSON records first", "error"); return; }
  const planId = S.setupPlanId;
  if (!planId) { notify("No active plan", "error"); return; }
  try {
    const records = JSON.parse(raw);
    const arr = Array.isArray(records) ? records : [records];
    const mapping = buildFieldMapping(arr);
    S.setupFieldMapping = mapping;
    const preview = await apiPost("/v1/setup/plans/" + planId + "/imports/preview", { records: arr, field_mapping: mapping });
    const previewEl = q("#import-preview-results");
    if (!previewEl) return;
    previewEl.innerHTML = '<div style="margin-top:8px;padding:12px;border:1px solid var(--border);border-radius:8px">' +
      '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:12px">' +
      '<div><strong>Total</strong><br>' + preview.total_records + ' records</div>' +
      '<div><strong>Matched</strong><br>' + preview.matched_count + ' w/ decisions</div>' +
      '<div><strong>Ignored</strong><br>' + (preview.ignored_count || 0) + '</div>' +
      '<div><strong>Replayable</strong><br>' + preview.replayable_count + '</div>' +
      '<div><strong>Need labels</strong><br>' + preview.needs_label_count + '</div>' +
      '<div><strong>Missing cassette</strong><br>' + preview.missing_cassette_count + '</div>' +
      '<div><strong>Evidence-only</strong><br>' + preview.evidence_only_count + '</div>' +
      '<div><strong>Scenario candidates</strong><br>' + preview.scenario_candidate_count + '</div>' +
      '<div><strong>Est. storage</strong><br>' + (preview.estimated_storage_gb || 0) + ' GB</div>' +
      '</div>' +
      (preview.sample_records && preview.sample_records.length ? '<div style="margin-top:8px;font-size:11px;color:var(--muted)">Sample: ' + preview.sample_records.map(s => esc(s.source_record_ref || "")).join(", ") + '</div>' : '') +
      (preview.missing_required_fields && preview.missing_required_fields.length ? '<div style="margin-top:8px;font-size:11px;color:var(--amber)">Missing fields: ' + preview.missing_required_fields.join(", ") + '</div>' : '') +
      '<div style="margin-top:8px;font-size:11px;color:var(--muted)">Auto-mapped: source_record_ref, business_function, expected_outcome, agent_id, elements</div>' +
      '<button class="btn" style="margin-top:12px" onclick="importRecords()">Confirm Import (' + preview.total_records + ' records)</button>' +
      '</div>';
  } catch (e) {
    notify("Preview failed: " + e.message, "error");
  }
}

function buildFieldMapping(records) {
  if (!records.length) return {};
  const sample = records[0];
  const mapping = {};
  const first = (keys) => keys.find(key => sample[key] !== undefined && sample[key] !== "");
  if (!sample.source_record_ref) { const key = first(["case_id", "ticket_id", "conversation_id", "record_id"]); if (key) mapping.source_record_ref = key; }
  if (!sample.elements) { const key = first(["bot_response", "events", "trace", "decision_path"]); if (key) mapping.elements = key; }
  if (!sample.expected_outcome) { const key = first(["human_resolution", "expected_decision", "label", "ground_truth"]); if (key) mapping.expected_outcome = key; }
  ["agent_id", "agent_version", "model_provider", "model_name", "policy_version", "business_function", "customer_message"].forEach(key => {
    if (sample[key] !== undefined && sample[key] !== "") mapping[key] = key;
  });
  return mapping;
}

const DISCOVERY_MAPPING_FIELDS = [
  ["source_record_ref", "Record reference"],
  ["elements", "Decision path / events"],
  ["expected_outcome", "Expected outcome"],
  ["business_function", "Business function"],
  ["agent_id", "Agent ID"],
  ["agent_version", "Agent version"],
  ["model_provider", "Model provider"],
  ["model_name", "Model name"],
  ["policy_version", "Policy version"],
];

function renderDiscoveryMapping(records) {
  const keys = records.flatMap(record => Object.keys(record)).filter((key, idx, all) => all.indexOf(key) === idx).sort();
  const option = (selected) => `<option value="">Not mapped</option>${keys.map(key => `<option value="${esc(key)}"${selected === key ? " selected" : ""}>${esc(key)}</option>`).join("")}`;
  return `<div class="discovery-mapping"><div class="section-title" style="margin:0 0 6px">Field Mapping</div><div class="section-sub">Confirm how this export maps into a Verification Record. Fields are read-only until you preview again.</div><div class="discovery-mapping-grid">${DISCOVERY_MAPPING_FIELDS.map(([field, label]) => `<label class="np-field"><span>${label}</span><select class="discovery-map" data-field="${field}">${option(S.discoveryMapping[field])}</select></label>`).join("")}</div><button class="btn btn-sm" onclick="applyDiscoveryMapping()">Preview with mapping</button></div>`;
}

async function ensureDiscoveryPlan() {
  // Discovery is a Setup phase. Keep the legacy shortcut on the same plan.
  if (S.setupPlanId) {
    S.discoveryPlanId = S.setupPlanId;
    return S.setupPlanId;
  }
  if (S.discoveryPlanId) {
    S.setupPlanId = S.discoveryPlanId;
    return S.discoveryPlanId;
  }
  const plan = await apiPost("/v1/setup/plans", {workflow_name: "Decision Discovery", workflow_type: "custom"});
  S.setupPlanId = plan.id;
  S.discoveryPlanId = plan.id;
  return plan.id;
}

function renderDiscoveryMarkup(embedded = false) {
  return `${embedded ? '<div class="setup-step-content">' : ''}<div class="section-title">Decision Discovery</div><div class="section-sub">Import decision events, preview what is worth proving, and commit only the records you select. This is the evidence intake phase of the active Setup plan.</div><section class="discovery-import-panel"><div class="discovery-input-row"><div class="np-field"><label>Format</label><select id="discovery-format"><option value="json">JSON</option><option value="jsonl">JSONL</option><option value="csv">CSV</option></select></div><div class="np-field discovery-file"><label>File</label><input id="discovery-file" type="file" accept=".json,.jsonl,.ndjson,.csv" onchange="loadDiscoveryFile(this)"></div></div><div class="np-field"><label>Decision event data</label><textarea id="discovery-content" rows="10" placeholder='[{"source_record_ref":"CASE-123","elements":[{"kind":"decision","payload":{"decision":"DENY"}}]}]'></textarea></div><div class="action-row"><button class="btn" onclick="previewDiscovery()">Preview findings</button><span class="section-sub" style="margin:0">JSON, JSONL, or CSV. Nothing is committed until you confirm.</span></div></section><div id="discovery-results">${S.discoveryFindings.length ? renderDiscoveryResults() : renderEmptyState("No preview yet", "Load decision events to see replayability and candidate findings.", "")}</div>${embedded ? '</div>' : ''}`;
}

async function renderSetupDiscoveryStep() {
  await ensureDiscoveryPlan();
  return renderDiscoveryMarkup(true);
}

async function renderDiscovery(c) {
  await ensureDiscoveryPlan();
  c.innerHTML = renderDiscoveryMarkup();
}

async function loadDiscoveryFile(input) {
  const file = input.files && input.files[0];
  if (!file) return;
  const ext = file.name.split(".").pop().toLowerCase();
  const format = ext === "ndjson" ? "jsonl" : ext;
  if (["json", "jsonl", "csv"].includes(format)) q("#discovery-format").value = format;
  q("#discovery-content").value = await file.text();
}

async function previewDiscovery() {
  const content = q("#discovery-content")?.value.trim();
  const format = q("#discovery-format")?.value || "json";
  if (!content) { notify("Add a decision export first", "error"); return; }
  try {
    await ensureDiscoveryPlan();
    const parsed = await apiPost(`/v1/setup/plans/${S.discoveryPlanId}/imports/parse`, {format, content});
    const records = parsed.records || [];
    const mapping = buildFieldMapping(records);
    S.discoveryRecords = records;
    S.discoveryMapping = mapping;
    const preview = await apiPost(`/v1/setup/plans/${S.discoveryPlanId}/imports/preview`, {records, field_mapping: mapping});
    S.discoveryFindings = preview.findings || [];
    const target = q("#discovery-results");
    if (target) target.innerHTML = renderDiscoveryResults(preview);
    notify(`Previewed ${preview.total_records} records`, "success");
  } catch (e) { notify("Discovery preview failed: " + e.message, "error"); }
}

function renderDiscoveryResults(preview = {}) {
  const findings = preview.findings || S.discoveryFindings;
  const rows = findings.map(f => `<tr><td><input type="checkbox" class="discovery-select" data-ref="${esc(f.source_record_ref)}" checked></td><td>${esc(f.source_record_ref || "—")}</td><td>${esc(f.trigger || "—")}</td><td>${esc(f.replayability || "—")}</td><td>${f.scenario_candidate ? "Candidate" : "Review"}</td><td>${esc(f.reason || "—")}</td></tr>`).join("");
  return `<section class="discovery-results-panel">${S.discoveryRecords.length ? renderDiscoveryMapping(S.discoveryRecords) : ""}<div class="discovery-metrics"><span><strong>${preview.total_records || S.discoveryRecords.length || 0}</strong> scanned</span><span><strong>${preview.matched_count || findings.length}</strong> matched</span><span><strong>${preview.replayable_count || 0}</strong> replayable</span><span><strong>${preview.needs_label_count || 0}</strong> need labels</span><span><strong>${preview.scenario_candidate_count || 0}</strong> candidates</span></div>${preview.missing_required_fields?.length ? `<div class="proof-pending">Missing mapped fields: ${esc(preview.missing_required_fields.join(", "))}</div>` : ""}${rows ? `<table><thead><tr><th>Select</th><th>Record</th><th>Finding</th><th>Replayability</th><th>Path</th><th>Reason</th></tr></thead><tbody>${rows}</tbody></table><div class="action-row" style="margin-top:12px"><button class="btn btn-green" onclick="commitDiscoverySelection()">Commit selected records</button></div>` : renderEmptyState("No findings", "No enabled selection rule matched these records.", "")}</section>`;
}

async function applyDiscoveryMapping() {
  const mapping = {};
  qa(".discovery-map").forEach(select => { if (select.value) mapping[select.dataset.field] = select.value; });
  S.discoveryMapping = mapping;
  try {
    await ensureDiscoveryPlan();
    const preview = await apiPost(`/v1/setup/plans/${S.discoveryPlanId}/imports/preview`, {records: S.discoveryRecords, field_mapping: mapping});
    S.discoveryFindings = preview.findings || [];
    const target = q("#discovery-results");
    if (target) target.innerHTML = renderDiscoveryResults(preview);
    notify(`Previewed ${preview.total_records} records with mapping`, "success");
  } catch (e) { notify("Mapping preview failed: " + e.message, "error"); }
}

async function commitDiscoverySelection() {
  const selected = Array.from(qa(".discovery-select")).filter(x => x.checked).map(x => x.dataset.ref);
  if (!selected.length) { notify("Select at least one finding", "error"); return; }
  try {
    await ensureDiscoveryPlan();
    const result = await apiPost(`/v1/setup/plans/${S.discoveryPlanId}/imports/commit`, {records: S.discoveryRecords, field_mapping: S.discoveryMapping, selected_source_record_refs: selected});
    notify(`Committed ${result.imported} Verification Record${result.imported === 1 ? "" : "s"}`, "success");
    S.discoveryCommitted = (result.imported || 0) > 0;
    S.onbReceived = S.onbReceived || (result.records && result.records[result.records.length - 1]) || {id: "discovery-imported"};
    S.discoveryFindings = result.discovery_findings || S.discoveryFindings;
    const target = q("#discovery-results");
    if (target) target.innerHTML = renderDiscoveryResults({findings: S.discoveryFindings, matched_count: S.discoveryFindings.length});
  } catch (e) { notify("Discovery commit failed: " + e.message, "error"); }
}



function openImportSetup() {
  renderDrawer("Batch / Log Import", '<div class="section-sub">Paste JSON records in setup step 5 to import. Supports Zendesk, Salesforce, ServiceNow, Intercom, CSV, and JSONL formats.</div>');
}

function openWebhookSetup() {
  renderDrawer("Webhook Setup", '<div class="section-sub">Webhook endpoint: POST /v1/webhooks/decision-records/{connector_id}</div><div class="section-title" style="margin-top:16px">Headers</div>' + renderCodeBlock("Authorization: Bearer <token>\nContent-Type: application/json") + '<div class="section-title" style="margin-top:16px">Payload</div>' + renderCodeBlock('{\n  "source_record_ref": "TKT-1234",\n  "events": [{"kind": "decision", "payload": {"decision": "DENY"}}]\n}'));
}

function openManualSubmissionForm() {
  renderDrawer("Manual Submission", '<div class="section-sub">Submit a decision directly from the Verification Records screen — best for complaints, overrides, and one-off reviews.');
}

// --- Replay player (reusable across scenarios) ---
const REPLAY_EVENTS = [
  { kind: "input", label: "Applicant intake", detail: "Thin-file personal loan application received" },
  { kind: "llm", label: "LLM decision call", detail: "Adverse-action reasoning over applicant + bureau evidence" },
  { kind: "http", label: "Credit bureau lookup", detail: "missing_evidence · 0 tradelines returned" },
  { kind: "policy", label: "Policy evaluation", detail: "underwriting-policy-v1.3 applied" },
  { kind: "decision", label: "Final decision", detail: "DENY (confidence 0.72)" },
];
let _replayEvents = REPLAY_EVENTS;
let _replayOriginal = "DENY";
let _replayReplayed = "DENY";
let _replayVerdict = "Failure deterministically reproduced from the sealed cassette — byte-for-byte identical inputs.";
let _replay = { i: -1, playing: false, timer: null };

function openReplayDrawer() {
  _replayEvents = REPLAY_EVENTS;
  _replayOriginal = "DENY"; _replayReplayed = "DENY";
  _replayVerdict = "Failure deterministically reproduced from the sealed cassette — byte-for-byte identical inputs.";
  _replay = { i: -1, playing: false, timer: null };
  renderDrawer("Replay · sealed cassette", `<div id="replay-player"></div>`);
  renderReplayPlayer();
  setTimeout(replayPlay, 350);
}

function renderReplayPlayer() {
  const el = document.getElementById("replay-player");
  if (!el) { if (_replay.timer) { clearInterval(_replay.timer); _replay.timer = null; } return; }
  const evs = _replayEvents;
  const pct = Math.max(0, Math.round(((_replay.i + 1) / evs.length) * 100));
  const finished = _replay.i >= evs.length - 1;
  el.innerHTML = `
    <div class="rp-head">
      <div class="rp-controls">
        <button class="btn btn-sm" onclick="replayToggle()" data-testid="replay-toggle-btn">${_replay.playing ? 'Pause' : (finished ? 'Replay again' : 'Play')}</button>
        <button class="btn btn-sm btn-outline" onclick="replayStep()" data-testid="replay-step-btn">Step</button>
        <button class="btn btn-sm btn-outline" onclick="replayRestart()">Restart</button>
      </div>
      <div class="rp-progress"><div class="rp-progress-bar" style="width:${pct}%"></div></div>
    </div>
    <div class="rp-events">
      ${evs.map((e, idx) => {
        const state = idx < _replay.i ? 'done' : idx === _replay.i ? 'active' : '';
        const ic = idx < _replay.i ? '&#10003;' : idx === _replay.i ? '&#9656;' : (idx + 1);
        return `<div class="rp-event ${state}">
          <div class="rp-icon">${ic}</div>
          <div style="min-width:0"><div class="rp-label">${esc(e.label)} <span class="trace-kind">${esc(e.kind)}</span></div><div class="rp-detail">${esc(e.detail)}</div></div>
        </div>`;
      }).join("")}
    </div>
    ${finished ? `
      <div class="rp-compare">
        <div class="rp-side"><span class="summary-block-label">Original</span><span class="decision-pill decision-fail">${esc(_replayOriginal)}</span></div>
        <div class="summary-arrow">&#8594;</div>
        <div class="rp-side"><span class="summary-block-label">Replayed</span><span class="decision-pill decision-fail">${esc(_replayReplayed)}</span></div>
      </div>
      <div class="comparison-verdict verdict-fail">${esc(_replayVerdict)}</div>
    ` : ""}`;
}

function replayPlay() {
  _replay.playing = true;
  if (_replay.timer) clearInterval(_replay.timer);
  _replay.timer = setInterval(() => {
    if (_replay.i >= _replayEvents.length - 1) { _replay.playing = false; clearInterval(_replay.timer); _replay.timer = null; renderReplayPlayer(); return; }
    _replay.i++;
    renderReplayPlayer();
  }, 950);
  renderReplayPlayer();
}
function replayToggle() {
  if (_replay.playing) { _replay.playing = false; if (_replay.timer) clearInterval(_replay.timer); renderReplayPlayer(); }
  else { if (_replay.i >= _replayEvents.length - 1) _replay.i = -1; replayPlay(); }
}
function replayStep() {
  _replay.playing = false; if (_replay.timer) clearInterval(_replay.timer);
  if (_replay.i < _replayEvents.length - 1) _replay.i++;
  renderReplayPlayer();
}
function replayRestart() { _replay.i = -1; replayPlay(); }

async function loadSampleData() {
  try { await apiPost("/v1/demo/catalog/seed"); notify("Sample data loaded", "success"); R(); }
  catch (e) { notify("Failed to load sample data: " + e.message, "error"); }
}

// ============================================================
// Guided demo — Northstar Air (inspired by Moffatt v. Air Canada, 2024)
// ============================================================
const NORTHSTAR = {
  company: "Northstar Air",
  agent: "Bereavement Support Bot",
  version: "support-bot-v42",
  fixedVersion: "support-bot-v43",
  model: "GPT-4o · Azure OpenAI",
  policy: "bereavement-policy-v7",
  source: "Salesforce Service Cloud",
  caseId: "Case #50093821",
  vrId: "vr-northstar-001",
  proofId: "pom-northstar-7a3f",
  readinessId: "por-northstar-91c2",
  original: "OFFER_RETROACTIVE_REFUND",
  expected: "ESCALATE_TO_HUMAN",
};
const NORTHSTAR_EVENTS = [
  { kind: "input", label: "Customer message", detail: "\u201CMy grandmother passed away. I already booked. Can I still get a bereavement fare refund?\u201D" },
  { kind: "http", label: "Policy lookup", detail: "Bereavement Policy API \u2192 retroactive_refund_allowed: false · human_review_required: true (bereavement-policy-v7)" },
  { kind: "llm", label: "Model call", detail: "GPT-4o · prompt support-policy-prompt-v42 · temp 0 · seed 12345" },
  { kind: "decision", label: "Bot response", detail: "\u201CYes, you can submit a refund request within 90 days.\u201D" },
  { kind: "decision", label: "Final decision", detail: "OFFER_RETROACTIVE_REFUND" },
];

function pill(text, kind) { return `<span class="decision-pill decision-${kind}">${esc(text)}</span>`; }

const DEMO_SCENES = [
  { tag: "Setup", render: demoIntro },
  { tag: "The failure", render: demoBadDecision },
  { tag: "Replay", render: demoReplay },
  { tag: "Answer key", render: demoLabel },
  { tag: "Verify fix", render: demoFix },
  { tag: "Proof", render: demoProof },
  { tag: "Scenario", render: demoPromote },
  { tag: "Gate blocked", render: demoGateFail },
  { tag: "Gate passed", render: demoGatePass },
  { tag: "Assured", render: demoEnd },
];

function renderDemo(c) {
  if (!S.demo || typeof S.demo.step !== "number") S.demo = { step: 0 };
  const on = q("#org-name"); if (on) on.textContent = "Northstar Air · demo";
  demoRenderScene(c);
}

function demoGo(step) {
  const c = q("#content"); if (!c) return;
  if (_replay.timer) { clearInterval(_replay.timer); _replay.timer = null; }
  S.demo.step = Math.max(0, Math.min(DEMO_SCENES.length - 1, step));
  demoRenderScene(c);
  const st = q("#demo-stage"); if (st) st.scrollTop = 0;
}

function demoRenderScene(c) {
  const step = S.demo.step;
  const scene = DEMO_SCENES[step];
  c.innerHTML = `
    <div class="demo-shell">
      <div class="demo-head">
        <div class="demo-eyebrow">Live demo · ${esc(NORTHSTAR.company)} · inspired by <em>Moffatt v. Air Canada</em> (2024)</div>
        <div class="demo-chapters">
          ${DEMO_SCENES.map((s, i) => `<button class="demo-chip ${i === step ? 'active' : i < step ? 'done' : ''}" onclick="demoGo(${i})" data-testid="demo-chip-${i}"><span class="demo-chip-num">${i < step ? '&#10003;' : i + 1}</span>${esc(s.tag)}</button>`).join("")}
        </div>
      </div>
      <div class="demo-stage" id="demo-stage">${scene.render()}</div>
      <div class="demo-nav">
        ${step > 0 ? `<button class="btn btn-outline" onclick="demoGo(${step - 1})" data-testid="demo-back-btn">Back</button>` : `<span></span>`}
        ${step < DEMO_SCENES.length - 1
          ? `<button class="btn" onclick="demoGo(${step + 1})" data-testid="demo-next-btn">${step === 0 ? 'Start the story' : 'Next'} &#8594;</button>`
          : `<button class="btn btn-green" onclick="demoGo(0)" data-testid="demo-restart-btn">Restart demo</button>`}
      </div>
    </div>`;
  if (scene.tag === "Replay") {
    _replayEvents = NORTHSTAR_EVENTS;
    _replayOriginal = NORTHSTAR.original; _replayReplayed = NORTHSTAR.original;
    _replayVerdict = "The wrong answer reproduces exactly from the sealed cassette — this is a real, provable failure, not a vague complaint.";
    _replay = { i: -1, playing: false, timer: null };
    renderReplayPlayer();
    setTimeout(replayPlay, 450);
  }
}

function demoIntro() {
  return `
    <div class="demo-hero">
      <h2>An AI support bot invents a refund policy</h2>
      <p>${esc(NORTHSTAR.company)}'s support bot told a grieving customer they could get a <strong>retroactive bereavement refund</strong>. The airline's actual policy says the opposite. In the real <em>Moffatt v. Air Canada</em> case, a tribunal held the airline liable for exactly this.</p>
      <p class="demo-hero-thesis">Notary captures that decision, replays it, verifies the fix, and turns the failure into a release gate — so the next bot release <strong>cannot repeat it</strong>.</p>
      <div class="demo-systems">
        <div class="demo-sys"><span class="demo-sys-label">Source system</span><span>${esc(NORTHSTAR.source)}</span></div>
        <div class="demo-sys"><span class="demo-sys-label">AI agent</span><span>${esc(NORTHSTAR.agent)}</span></div>
        <div class="demo-sys"><span class="demo-sys-label">Policy source</span><span>Bereavement Policy API</span></div>
        <div class="demo-sys"><span class="demo-sys-label">Release system</span><span>GitHub Actions</span></div>
      </div>
      <p class="demo-hint">Notary plugs into systems ${esc(NORTHSTAR.company)} already uses. Press <strong>Start the story</strong>.</p>
    </div>`;
}

function demoBadDecision() {
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">The failure</span><h2>One AI decision worth proving</h2></div>
      <div class="demo-two-col">
        <div>
          <div class="demo-card">
            <div class="demo-card-head">Verification Record <span class="mono demo-card-id">${esc(NORTHSTAR.vrId)}</span></div>
            <div class="kv"><span class="kv-label">Source</span><span class="kv-value">${esc(NORTHSTAR.source)} · ${esc(NORTHSTAR.caseId)}</span></div>
            <div class="kv"><span class="kv-label">Agent</span><span class="kv-value">${esc(NORTHSTAR.agent)} · ${esc(NORTHSTAR.version)}</span></div>
            <div class="kv"><span class="kv-label">Model</span><span class="kv-value">${esc(NORTHSTAR.model)}</span></div>
            <div class="kv"><span class="kv-label">Policy version</span><span class="kv-value">${esc(NORTHSTAR.policy)}</span></div>
            <div class="kv"><span class="kv-label">Environment</span><span class="kv-value">production</span></div>
            <div class="kv"><span class="kv-label">Replayability</span><span class="kv-value" style="color:var(--green)">replayable</span></div>
          </div>
          <div class="demo-contradiction">
            <div class="demo-contra-row"><span class="demo-contra-tag">Policy says</span><span>No retroactive refund. Human review required.</span></div>
            <div class="demo-contra-row bad"><span class="demo-contra-tag">Bot said</span><span>\u201CYes, submit a refund request within 90 days.\u201D</span></div>
          </div>
          <div class="demo-decisions">
            <div><span class="summary-block-label">Original decision</span>${pill(NORTHSTAR.original, "fail")}</div>
            <span class="summary-arrow">&#8594;</span>
            <div><span class="summary-block-label">Should have been</span>${pill(NORTHSTAR.expected, "pass")}</div>
          </div>
        </div>
        <div>
          <div class="demo-scene-kicker" style="margin-bottom:10px">Decision evidence graph</div>
          <div class="investigation-trace">
            ${NORTHSTAR_EVENTS.map((e, i) => `
              <div class="investigation-trace-row">
                <span class="trace-index">${i + 1}</span>
                <span class="trace-state trace-done">&#10003;</span>
                <div><div style="font-weight:600;color:var(--text);font-size:12px">${esc(e.label)}</div><div class="trace-detail">${esc(e.detail)}</div></div>
                <span class="trace-kind">${esc(e.kind)}</span>
              </div>`).join("")}
          </div>
        </div>
      </div>
    </div>`;
}

function demoReplay() {
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">Replay</span><h2>Reproduce the failure from sealed evidence</h2></div>
      <p class="demo-scene-lead">Notary replays the exact recorded conditions — the same customer message, the same policy response, the same model settings. If the bad answer comes back, it's a real, provable failure.</p>
      <div class="demo-card"><div id="replay-player"></div></div>
    </div>`;
}

function demoLabel() {
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">Answer key</span><h2>A human decides the correct outcome</h2></div>
      <p class="demo-scene-lead">Notary doesn't decide what's right — ${esc(NORTHSTAR.company)}'s own team labels the expected outcome. That human label becomes the answer key every future release is tested against.</p>
      <div class="demo-card demo-label-card">
        <div class="kv"><span class="kv-label">Reviewer</span><span class="kv-value">Customer Support QA Lead</span></div>
        <div class="kv"><span class="kv-label">Expected outcome</span><span class="kv-value">${pill(NORTHSTAR.expected, "pass")}</span></div>
        <div class="kv"><span class="kv-label">Reason</span><span class="kv-value" style="text-align:right;max-width:60%">Bot must not invent refund policy or contradict official fare policy. When policy requires human review, escalate.</span></div>
      </div>
    </div>`;
}

function demoFix() {
  const code = `{\n  "require_policy_match_for_refund_claims": true,\n  "escalate_when_policy_requires_human_review": true\n}`;
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">Verify fix</span><h2>Prove the fix works under the same conditions</h2></div>
      <p class="demo-scene-lead">Apply the fix, then replay the <em>identical</em> sealed record. If the outcome changes to the expected answer, the fix is verified — not hoped.</p>
      <div class="demo-two-col">
        <div>
          <div class="demo-scene-kicker" style="margin-bottom:8px">Fix configuration</div>
          ${renderCodeBlock(code)}
        </div>
        <div>
          <div class="before-after">
            <div><span class="summary-block-label">Before fix</span><strong style="color:var(--red)">${esc(NORTHSTAR.original)}</strong><p>${esc(NORTHSTAR.version)}</p></div>
            <div class="before-after-arrow">&#8594;</div>
            <div><span class="summary-block-label">After fix</span><strong style="color:var(--green)">${esc(NORTHSTAR.expected)}</strong><p>${esc(NORTHSTAR.fixedVersion)}</p></div>
          </div>
          <div class="comparison-verdict" style="background:var(--green-bg);color:var(--green);border:1px solid rgba(16,185,129,.25);margin-top:14px">Fix verified — matches the expected outcome under byte-identical replay.</div>
        </div>
      </div>
    </div>`;
}

function demoProof() {
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">Proof</span><h2>Issue a signed Proof of Mitigation</h2></div>
      <p class="demo-scene-lead">A bounded, auditable artifact — it claims exactly what was fixed, under what tested conditions, and nothing more.</p>
      <div class="proof-bundle">
        <h3>&#128273; Proof of Mitigation <span class="mono" style="font-size:11px;color:var(--muted);font-weight:400">${esc(NORTHSTAR.proofId)}</span></h3>
        <div class="kv"><span class="kv-label">Scenario</span><span class="kv-value">Bereavement refund policy misrepresentation</span></div>
        <div class="kv"><span class="kv-label">Source</span><span class="kv-value">${esc(NORTHSTAR.caseId)}</span></div>
        <div class="kv"><span class="kv-label">Replay method</span><span class="kv-value">sealed cassette</span></div>
        <div class="kv"><span class="kv-label">Original &#8594; fixed</span><span class="kv-value">${esc(NORTHSTAR.original)} \u2192 ${esc(NORTHSTAR.expected)}</span></div>
        <div class="kv"><span class="kv-label">Fix reference</span><span class="kv-value">${esc(NORTHSTAR.fixedVersion)}</span></div>
        <div class="kv"><span class="kv-label">Claim scope</span><span class="kv-value">verified for this scenario only</span></div>
        <div class="kv"><span class="kv-label">Known limitations</span><span class="kv-value" style="text-align:right;max-width:60%">Not a claim of general AI safety.</span></div>
        <div class="kv"><span class="kv-label">Seal</span><span class="kv-value mono" style="color:var(--green)">sha256:8f21c4…verified</span></div>
      </div>
    </div>`;
}

function demoPromote() {
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">Scenario</span><h2>Turn the failure into a permanent regression test</h2></div>
      <p class="demo-scene-lead">One real failure becomes a reusable Scenario — replayed against every future bot release.</p>
      <div class="demo-card">
        <div class="demo-card-head">Scenario <span class="badge badge-certified" style="margin-left:8px">Active</span></div>
        <div class="kv"><span class="kv-label">Name</span><span class="kv-value">Bereavement refund policy misrepresentation</span></div>
        <div class="kv"><span class="kv-label">Source</span><span class="kv-value">${esc(NORTHSTAR.source)} · ${esc(NORTHSTAR.caseId)}</span></div>
        <div class="kv"><span class="kv-label">What failed</span><span class="kv-value" style="text-align:right;max-width:60%">Bot offered a retroactive refund the policy did not allow.</span></div>
        <div class="kv"><span class="kv-label">Expected outcome</span><span class="kv-value">${pill(NORTHSTAR.expected, "pass")}</span></div>
        <div class="kv"><span class="kv-label">Replay method</span><span class="kv-value">sealed cassette</span></div>
      </div>
    </div>`;
}

function demoGateGraph(status) {
  const pass = status === "pass";
  return `
    <div class="gate-impact">
      <span class="gate-node gate-capture">Capture</span><span class="gate-line"></span>
      <span class="gate-node gate-capture">Scenario</span><span class="gate-line"></span>
      <span class="gate-node ${pass ? 'gate-pass' : 'gate-fail'}">Release Gate: ${pass ? 'PASS' : 'FAIL'}</span><span class="gate-line"></span>
      <span class="gate-node ${pass ? 'gate-pass' : 'gate-muted'}">${pass ? 'Ship v43' : 'Blocked'}</span>
    </div>`;
}

function demoGateFail() {
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">Gate blocked</span><h2>The old release cannot ship</h2></div>
      <p class="demo-scene-lead">Run the Scenario against the buggy release in CI. The gate blocks it.</p>
      ${demoGateGraph("fail")}
      <div class="demo-gate demo-gate-fail">
        <div class="demo-gate-head"><span class="badge badge-red">FAIL</span> Release Gate · ${esc(NORTHSTAR.version)}</div>
        <div class="kv"><span class="kv-label">Failed scenario</span><span class="kv-value">Bereavement refund policy misrepresentation</span></div>
        <div class="kv"><span class="kv-label">Expected</span><span class="kv-value">${esc(NORTHSTAR.expected)}</span></div>
        <div class="kv"><span class="kv-label">Actual</span><span class="kv-value" style="color:var(--red)">${esc(NORTHSTAR.original)}</span></div>
        <div class="kv"><span class="kv-label">Action</span><span class="kv-value">Fix policy-validation layer and rerun gate</span></div>
      </div>
    </div>`;
}

function demoGatePass() {
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">Gate passed</span><h2>The fixed release is cleared to ship</h2></div>
      <p class="demo-scene-lead">Same gate, fixed release. All required scenarios pass and Notary issues a Proof of Readiness.</p>
      ${demoGateGraph("pass")}
      <div class="demo-gate demo-gate-pass">
        <div class="demo-gate-head"><span class="badge badge-certified">PASS</span> Release Gate · ${esc(NORTHSTAR.fixedVersion)}</div>
        <div class="kv"><span class="kv-label">Policy</span><span class="kv-value">High-risk support policy gate</span></div>
        <div class="kv"><span class="kv-label">Required scenarios</span><span class="kv-value">3 passed · 0 failed · 0 errored</span></div>
        <div class="kv"><span class="kv-label">Actual</span><span class="kv-value" style="color:var(--green)">${esc(NORTHSTAR.expected)}</span></div>
        <div class="kv"><span class="kv-label">Certificate</span><span class="kv-value mono">${esc(NORTHSTAR.readinessId)}</span></div>
      </div>
      ${renderCodeBlock(`curl -X POST https://api.getnotary.ai/v1/release-gate/checks \\\n  -H "Authorization: Bearer ntry-..." \\\n  -d '{"release":"${NORTHSTAR.fixedVersion}","policy":"support-bot-high-risk"}'`)}
    </div>`;
}

function demoEnd() {
  const tiles = [
    ["Verification Record", "certified"],
    ["Proof of Mitigation", "issued"],
    ["Scenario", "active"],
    ["Latest Scenario Run", "passed"],
    ["Readiness Check", "passed"],
    ["Release Gate", "pass"],
  ];
  return `
    <div class="demo-scene">
      <div class="demo-scene-title"><span class="demo-scene-kicker">Assured</span><h2>One AI failure is now permanent release assurance</h2></div>
      <div class="stat-grid">
        ${tiles.map(([label, val]) => `<div class="stat"><div class="stat-val" style="font-size:16px;color:var(--green);font-family:var(--fh)">&#10003; ${esc(val)}</div><div class="stat-label">${esc(label)}</div></div>`).join("")}
      </div>
      <div class="next-action-card" style="margin-top:8px" onclick="nav('setup')">
        <div class="title">Ready to connect your own AI systems?</div>
        <div class="detail">Head to Setup to register a system and send your first Verification Record.</div>
      </div>
    </div>`;
}

async function sendHarborlineTestCapture() {
  const btn = q("#harborline-test-capture-btn");
  if (btn) { btn.disabled = true; btn.textContent = "Sending..."; }
  try {
    const snapshot = {
      schema_version: 1,
      timestamp: new Date().toISOString(),
      elements: [
        { kind: "input", payload: { applicant_id: "HLCU-PL-0427", product: "personal_loan", thin_file: true } },
        { kind: "llm", payload: { prompt: "Adverse-action decision for HLCU-PL-0427", response: "Decision: DENY — thin file, insufficient bureau evidence" } },
        { kind: "http", payload: { request: { method: "POST", url: "/credit-bureau/evidence" }, response: { status: "missing_evidence", tradelines: 0 }, status: 200 } },
        { kind: "policy", payload: { version: "underwriting-policy-v1.3", rule: "thin_file_missing_bureau → route to underwriting review" } },
        { kind: "decision", payload: { decision: "DENY", confidence: 0.72 } },
      ],
    };
    const r = await apiPost("/v1/verification-records/from-snapshot?agent_id=browser-sdk-demo", snapshot);
    const vrId = r.id;
    const vr = await apiGet("/v1/verification-records/" + vrId);
    S.setupTestCapture = {
      id: vr.id,
      applicant_id: "HLCU-PL-0427",
      decision: "DENY",
      expected: "UNDERWRITING_REVIEW",
      systems: ["Loan Origination System", "Credit Bureau Evidence", "Underwriting Policy Rules", "AI Decision Agent"],
      root_hash: vr.root_hash || "",
      replayability: vr.replayability || "Pending assessment",
    };
    notify("Meridian test capture created", "success");
    renderSetupStep(9); // jump to readiness
  } catch (e) {
    notify("Test capture failed: " + e.message, "error");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Send Test Capture"; }
  }
}

async function renderSetupReplayStep() {
  const wf = S.setupWorkflow;
  const vrs = await apiGet("/v1/verification-records").catch(() => []);
  const nonDemo = vrs.filter(v => v.source_type !== "demo_seed");
  const target = nonDemo[nonDemo.length - 1] || vrs[vrs.length - 1];
  if (!target) {
    return '<div class="setup-step-content"><h2>Review replayability</h2><p class="setup-lead">No Verification Records found. Send or import records first.</p></div>';
  }
  const replayState = target.replayability || "unknown";
  const missing = target.missing_prerequisites || [];
  const statusColor = replayState === "replayable" ? "var(--green)" : replayState === "requires_human_label" ? "var(--amber)" : "var(--red)";
  return '<div class="setup-step-content">' +
    '<h2>Review replayability</h2>' +
    '<p class="setup-lead">Notary assessed your latest record for deterministic replay.' + (wf ? ' Workflow: ' + esc(wf.name) : '') + '</p>' +
    '<div class="int-card">' +
    '<div style="display:flex;justify-content:space-between;align-items:center">' +
    '<div><h4>' + esc(target.id || "Verification Record") + '</h4><p>Created ' + esc(target.created_at || "") + '</p></div>' +
    '<span class="badge" style="background:' + statusColor + ';color:#fff">' + esc(replayState) + '</span>' +
    '</div>' +
    '<div class="packet-grid" style="margin-top:12px">' +
    '<div class="packet-field"><span>Replayability</span><span>' + esc(replayState) + '</span></div>' +
    '<div class="packet-field"><span>Events captured</span><span>' + (target.events ? target.events.length : 0) + '</span></div>' +
    '<div class="packet-field"><span>Missing prerequisites</span><span>' + (missing.length ? missing.join(", ") : "None") + '</span></div>' +
    '</div>' +
    '</div>' +
    (replayState === "requires_human_label" ? '<div style="margin-top:12px"><p style="font-size:12px;color:var(--amber)">Add an expected outcome label to enable replay.</p></div>' : '') +
    (replayState === "missing_context" ? '<div style="margin-top:12px"><p style="font-size:12px;color:var(--red)">Missing: ' + missing.join(", ") + '</p></div>' : '') +
    (replayState === "replayable" ? '<div style="margin-top:12px"><button class="btn btn-green" onclick="openReplayDrawer()">Watch replay</button></div>' : '') +
    '</div>';
}

async function renderSetupReadinessStep() {
  let planId = S.setupPlanId;
  if (!planId) {
    try {
      const plan = await apiPost("/v1/setup/plans", {});
      S.setupPlanId = plan.id;
      planId = plan.id;
    } catch (e) {
      return '<div class="setup-step-content"><h2>Readiness Assessment</h2><p class="setup-lead">Could not create setup plan: ' + esc(e.message) + '</p></div>';
    }
  }
  const readiness = await apiGet("/v1/setup/plans/" + planId + "/readiness").catch(() => null);
  if (!readiness) {
    return '<div class="setup-step-content"><h2>Readiness Assessment</h2><p class="setup-lead">Could not load readiness data. Complete previous steps first.</p></div>';
  }
  const checks = [
    {label: "Create Verification Records", status: readiness.can_create_records ? "pass" : "fail", detail: readiness.can_create_records ? "Plan can create records from captures or imports." : "Complete steps 1-5 to enable record creation."},
    {label: "Deterministic Replay", status: readiness.can_replay ? "pass" : "fail", detail: readiness.can_replay ? "Records can be replayed for verification." : "Evidence contract and capture method required."},
    {label: "Issue Proof", status: readiness.can_issue_proof ? "pass" : "fail", detail: readiness.can_issue_proof ? "Notary can issue tamper-proof certificates." : "Replay-ready records and expected outcomes required."},
    {label: "Create Scenarios", status: readiness.can_create_scenarios ? "pass" : "fail", detail: readiness.can_create_scenarios ? "Scenario Candidates can be promoted from replayable records." : "Replayable records with labels required."},
    {label: "Create Release Gate", status: readiness.can_create_release_gate ? "pass" : "fail", detail: readiness.can_create_release_gate ? "Readiness policy gated with scenarios." : "Promote a scenario and create a readiness policy."},
  ];
  const passed = checks.filter(c => c.status === "pass").length;
  const total = checks.length;
  const pct = Math.round((passed / total) * 100);
  return `
    <div class="setup-step-content">
      <h2>Readiness Assessment</h2>
      <p class="setup-lead">Notary evaluated your plan against production readiness criteria.</p>
      <div style="margin-bottom:16px">
        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
          <span>Readiness: ${passed}/${total} checks passed</span>
          <span>${pct}%</span>
        </div>
        <div class="setup-progress"><div class="setup-progress-bar" style="width:${pct}%"></div></div>
      </div>
      ${checks.map(c => `
        <div class="int-card" style="margin-bottom:8px;padding:12px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <strong>${esc(c.label)}</strong>
              <div style="font-size:12px;color:var(--muted);margin-top:4px">${esc(c.detail)}</div>
            </div>
            <span class="badge ${c.status === 'pass' ? 'badge-built' : 'badge-planned'}">${c.status === 'pass' ? 'Ready' : 'Not ready'}</span>
          </div>
        </div>
      `).join("")}
      ${(readiness.missing_prerequisites || []).length ? `<div style="margin-top:16px;padding:12px;border:1px dashed var(--amber);border-radius:8px">
        <strong style="font-size:12px;color:var(--amber)">Missing prerequisites:</strong>
        <ul style="font-size:11px;color:var(--muted);margin:4px 0 0;padding-left:16px">
          ${readiness.missing_prerequisites.map(m => `<li>${esc(m)}</li>`).join("")}
        </ul>
      </div>` : ""}
      ${(readiness.next_actions || []).length ? `<div style="margin-top:12px;padding:12px;border:1px solid var(--border);border-radius:8px">
        <strong style="font-size:12px">Next actions:</strong>
        <ul style="font-size:11px;color:var(--muted);margin:4px 0 0;padding-left:16px">
          ${readiness.next_actions.map(a => `<li>${esc(a)}</li>`).join("")}
        </ul>
      </div>` : ""}
      <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px">
        <div style="padding:8px;border:1px solid var(--border);border-radius:6px">
          <strong>Est. records/month</strong><br>${readiness.estimated_monthly_records || 0}
        </div>
        <div style="padding:8px;border:1px solid var(--border);border-radius:6px">
          <strong>Est. storage</strong><br>${readiness.estimated_storage_gb || 0} GB/month
        </div>
      </div>
    </div>`;
}

async function renderSetupStep(step) {
  S.setupStep = step;
  const contentEl = q("#setup-step-content");
  if (!contentEl) return;
  let content = "";
  switch (SETUP_STEPS[step].id) {
    case "objective": content = await renderSetupObjectiveStep(); break;
    case "workflow": content = await renderSetupWorkflowStep(); break;
    case "ai-system": content = await renderOnbRegisterStep(); break;
    case "evidence": content = await renderEvidenceSourcesStep(); break;
    case "capture": content = await renderSetupCaptureStep(); break;
    case "selection-rules": content = await renderSetupSelectionRulesStep(); break;
    case "discovery": content = await renderSetupDiscoveryStep(); break;
    case "send": content = await renderOnbSendStep(); break;
    case "replay": content = await renderSetupReplayStep(); break;
    case "readiness": content = await renderSetupReadinessStep(); break;
  }
  contentEl.innerHTML = content;
  const navSlot = q("#setup-nav-slot");
  if (navSlot) navSlot.innerHTML = renderSetupNav(step);
  const tracker = q("#setup-tracker");
  if (tracker) tracker.innerHTML = renderSetupTrackerInner(step);
}

async function renderSetup(c) {
  c.innerHTML = sk(40);
  const step = typeof S.setupStep === "number" ? S.setupStep : 0;
  S.setupStep = step;
  try {
    if (!S.setupPlanId) {
      const plan = await apiPost("/v1/setup/plans", {});
      S.setupPlanId = plan.id;
    }
  } catch (e) {
    // will surface in step rendering
  }
  c.innerHTML = `
    <div class="setup-hero">
      <div class="setup-hero-copy">
        <div class="eyebrow">Decision Automation Setup</div>
        <h2>Set up AI Decision Assurance</h2>
        <p>Define the AI decision you want to assure, register the system that makes it, choose what evidence matters, and create a Release Gate — all in one flow.</p>
      </div>
    </div>
    <div class="setup-shell">
      <aside class="setup-tracker" id="setup-tracker"></aside>
      <div class="setup-pane">
        <div id="setup-step-content"></div>
        <div id="setup-nav-slot"></div>
      </div>
    </div>
  `;
  renderSetupStep(step);
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
    <div class="section-title">2. Capture a decision (Python)</div>
    ${renderCodeBlock(`from notary_sdk import RunCapture\n\ncapture = RunCapture(secret_key=b"your-secret-key")\ncapture.capture_llm(prompt="loan app #1234", response="score: 620")\ncapture.capture_tool(method="POST", url="/score", response={"score": 620})\ncapture.capture_decision(decision="DENY")\nsnapshot = capture.finalize()`)}
    <div class="section-title">3. Submit to Notary API</div>
     ${renderCodeBlock(`import requests\n\nrequests.post(\n  "https://api.getnotary.ai/v1/verification-records/from-snapshot",\n  headers={"Authorization": "Bearer ${esc(S.token || 'your-token-here')}"},\n  json=snapshot.to_dict()\n)`)}
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
    };
    const r = await apiPost("/v1/verification-records/from-snapshot", snapshot);
    notify("Created Verification Record " + r.id, "success");
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
  const showWelcome = systems.length === 0 && !editing && !selectedSystemId;
  c.innerHTML = `
    <h2 style="margin-bottom:4px">Integrations & Capture</h2>
    <p class="section-sub" style="margin-bottom:16px">Connect AI systems and configure how Notary receives and handles decision evidence.</p>
    ${renderIntegrationsStats(status)}
    ${showWelcome ? renderIntegrationsWelcome() : ""}
    <div id="ic-workspace">
      ${editing ? renderIntegrationsForm() : (
        selectedSystemId ? renderAISystemDetail(selectedSystemId) : (showWelcome ? "" : renderIntegrationsSystemList(systems))
      )}
    </div>`;
}

function renderIntegrationsWelcome() {
  return `
    <div style="max-width:560px;margin:16px 0 24px">
      <div class="section-title" style="margin:0 0 8px">Get started</div>
      <p style="font-size:13px;color:var(--muted);margin-bottom:16px">Three steps to activate decision capture for your AI systems.</p>
      <div style="display:flex;gap:16px;margin-bottom:20px">
        <div class="ic-step-card">
          <div class="ic-step-number">1</div>
          <div><strong>Register</strong><div style="font-size:11px;color:var(--muted)">Name your AI system, type, endpoint, owners</div></div>
        </div>
        <div class="ic-step-connector">→</div>
        <div class="ic-step-card">
          <div class="ic-step-number">2</div>
          <div><strong>Connect</strong><div style="font-size:11px;color:var(--muted)">Add capture sources, configure field rules</div></div>
        </div>
        <div class="ic-step-connector">→</div>
        <div class="ic-step-card">
          <div class="ic-step-number">3</div>
          <div><strong>Activate</strong><div style="font-size:11px;color:var(--muted)">Validate coverage, flip the switch</div></div>
        </div>
      </div>
      <button class="btn" onclick="S._ic_editing={};renderIntegrations(q('#main-content'))">Register Your First AI System</button>
    </div>`;
}

function renderIntegrationsChooseExperience() {
  return `
    <h2 style="margin-bottom:20px">Welcome to Notary</h2>
    <p style="font-size:14px;color:var(--muted);margin-bottom:24px;max-width:600px">Choose how you want to get started with AI Decision Assurance.</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:720px">
      <div class="ic-experience-card" onclick="nav('setup')" style="cursor:pointer">
        <div class="ic-experience-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 20 12 6 21 6 3"/></svg></div>
        <h3>Explore the Demo</h3>
        <p>See Notary in action with a preconfigured Meridian Credit Union lending scenario. Walk through the full assurance loop — capture, replay, fix, proof, and release gate.</p>
        <span class="badge badge-demo" style="margin-top:12px">GUIDED DEMO</span>
      </div>
      <div class="ic-experience-card ic-experience-primary" onclick="S._ic_experience_chosen=true;renderIntegrations(q('#main-content'))" style="cursor:pointer">
        <div class="ic-experience-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></div>
        <h3>Set Up Your Organization</h3>
        <p>Register your AI systems, connect capture sources, and configure evidence handling. No assumptions about your industry or workflow.</p>
        <span class="badge badge-built" style="margin-top:12px">GET STARTED</span>
      </div>
    </div>
    <p style="font-size:11px;color:var(--dim);margin-top:20px">The demo is a guided walkthrough. Customer onboarding starts with zero assumptions.</p>`;
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
      const created = await apiPost("/v1/setup/ai-systems", body);
      notify("System registered", "success");
      S._ic_selected_system = created.id;
    }
    S._ic_editing = null;
    renderIntegrations(q("#main-content"));
  } catch (e) {
    notify("Failed: " + e.message, "error");
  }
}

async function editAISystem(systemId) {
  const system = await apiGet("/v1/setup/ai-systems/" + systemId).catch(() => null);
  if (system) {
    S._ic_editing = system;
    renderAISystemDetail(systemId);
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
      ${systems.map(s => {
        const nextHint = s.status === "draft" ? "Add capture sources" : s.status === "configured" ? "Validate & activate" : s.status === "active" ? "Capture active" : "";
        return `
        <div class="ic-system-row" onclick="S._ic_selected_system='${s.id}';renderIntegrations(q('#main-content'))">
          <div style="display:flex;align-items:center;gap:12px;flex:1">
            <div class="ic-system-icon">${s.system_type === "agent" ? "🤖" : s.system_type === "model_service" ? "⚡" : s.system_type === "decision_engine" ? "⚙" : "📱"}</div>
            <div>
              <strong>${esc(s.name)}</strong>
              <div style="font-size:11px;color:var(--muted)">${esc(s.system_type)} · ${s.deployment_version ? esc(s.deployment_version) : "no version"}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <span class="badge badge-${s.status === "active" ? "green" : s.status === "draft" ? "planned" : "ingested"}">${esc(s.status)}</span>
            ${nextHint ? `<span style="font-size:10px;color:var(--muted)">${nextHint}</span>` : ""}
          </div>
          <span style="color:var(--dim);font-size:16px">→</span>
        </div>`;
      }).join("")}
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

  const statusSteps = ["draft", "configured", "validated", "active"];
  const statusIdx = statusSteps.indexOf(system.status);
  c.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <button class="btn btn-outline btn-sm" onclick="S._ic_selected_system=null;S._ic_system_tab=null;renderIntegrations(q('#main-content'))">← Back</button>
      <h3 style="margin:0">${esc(system.name)}</h3>
      <span class="badge badge-${system.status === "active" ? "green" : system.status === "draft" ? "planned" : "ingested"}">${esc(system.status)}</span>
      <button class="btn btn-outline btn-sm" onclick="editAISystem('${systemId}')">Edit</button>
    </div>
    <div class="ic-status-bar">${statusSteps.map(function(s, i) {
      return '<div class="ic-status-step' + (i <= statusIdx ? ' done' : '') + (i === statusIdx ? ' current' : '') + '"><span class="ic-status-dot"></span><span>' + s + '</span></div>';
    }).join('<span class="ic-status-line"></span>')}</div>
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
  const hasConnected = connectors.some(c => c.status === "connected");
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
        <p>No capture sources connected yet. Add a connector to start receiving decision evidence from your AI system.</p>
        <div style="margin-top:12px;font-size:11px;color:var(--muted)">After creating a connector, click <strong>Test</strong> to verify the connection, then <strong>View Sample</strong> to inspect captured evidence.</div>
      </div>
    ` : `
    <div style="display:grid;gap:8px">
      ${connectors.map(c => {
        var badgeColor = c.status === "connected" ? "green" : c.status === "error" ? "red" : "planned";
        var statusLabel = c.status === "not_configured" ? "not configured" : c.status;
        return `
        <div class="ic-connector-row">
          <div style="flex:1">
            <strong>${esc(c.name || c.connector_type)}</strong>
            <div style="font-size:11px;color:var(--muted)">${esc(c.connector_type)}${c.last_tested_at ? " · last tested " + esc(c.last_tested_at) : ""}</div>
          </div>
          <span class="badge badge-${badgeColor}">${esc(statusLabel)}</span>
          <div class="action-row">
            <button class="btn btn-outline btn-sm" onclick="testConnector('${c.id}','${system.id}')">Test</button>
            <button class="btn btn-outline btn-sm" onclick="viewConnectorSamples('${c.id}','${system.id}')" ${c.status !== "connected" ? "disabled title='Test the connector first'" : ""}>View Sample</button>
          </div>
        </div>`;
      }).join("")}
    </div>
    ${!hasConnected ? '<div style="margin-top:8px;font-size:11px;color:var(--muted);text-align:center">Test each connector to verify connectivity before viewing evidence samples.</div>' : ""}`}`;
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
  const sysType = system.system_type || "agent";
  const nodeConfigs = {
    agent: {model: "Agent", processLabel: "Agent Runtime", toolLabel: "Tool Calls"},
    model_service: {model: "Model", processLabel: "Model Service", toolLabel: "API Responses"},
    decision_engine: {model: "Engine", processLabel: "Rules Engine", toolLabel: "Data Lookups"},
    ai_enabled_app: {model: "Feature", processLabel: "AI Feature", toolLabel: "External APIs"},
  };
  const cfg = nodeConfigs[sysType] || nodeConfigs.agent;
  return `
    <div style="margin:16px 0">
      <div class="section-title" style="margin:0 0 8px">Inspect Captured Evidence</div>
      <p class="section-sub">When a decision arrives, Notary captures the evidence flow through your system.${sample ? "" : " Connect a capture source and view a sample to see it."}</p>
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
            <div class="ic-evidence-node-header"><span>${cfg.model}</span><span class="ic-evidence-node-type" style="background:rgba(59,130,212,.15);color:#3b82d4">process</span></div>
            <div class="ic-evidence-node-items">${cfg.processLabel} · Prompt/configuration · ${system.deployment_version || "version unknown"}</div>
          </div>
          <div class="ic-evidence-arrow">↓ ↑</div>
          <div class="ic-evidence-node">
            <div class="ic-evidence-node-header"><span>${cfg.toolLabel}</span><span class="ic-evidence-node-type" style="background:rgba(245,158,11,.15);color:#f59e0b">external</span></div>
            <div class="ic-evidence-node-items">${system.external_caller ? "External APIs · Third-party services" : "Internal services · Policy lookups"}</div>
          </div>
          <div class="ic-evidence-arrow">↓</div>
          <div class="ic-evidence-node">
            <div class="ic-evidence-node-header"><span>Policies</span><span class="ic-evidence-node-type" style="background:rgba(124,92,216,.15);color:#7c5cd8">config</span></div>
            <div class="ic-evidence-node-items">Active policies · Rules applied · Config version</div>
          </div>
          <div class="ic-evidence-arrow">↓</div>
          <div class="ic-evidence-node">
            <div class="ic-evidence-node-header"><span>Decision</span><span class="ic-evidence-node-type" style="background:rgba(34,197,94,.15);color:#22c55e">output</span></div>
            <div class="ic-evidence-node-items">Final outcome from ${esc(system.name)}</div>
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
          <p>No captured evidence to inspect yet.</p>
          <div style="margin-top:8px;font-size:12px;color:var(--muted)">Go to the <strong>Connectors</strong> tab, add a capture source, then click <strong>View Sample</strong> to see the evidence flow through your system.</div>
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
  const canActivate = hasCoverage && (coverage.decision_detected && coverage.input_captured && coverage.final_decision_captured);
  const showActivate = system.status !== "active" && (validationRuns.length > 0 || canActivate);
  return `
    <div style="margin:16px 0">
      <div class="section-title" style="margin:0 0 8px">Capture Coverage Validation</div>
      <p class="section-sub">Run validation to assess whether the current setup would produce complete, replayable evidence if a decision arrived now.</p>
      <div style="display:flex;gap:12px;margin-bottom:16px">
        <button class="btn" onclick="runValidation('${system.id}')" id="ic-val-btn">Run Validation</button>
        ${showActivate ? `<button class="btn btn-green" onclick="activateSystem('${system.id}')">Activate Capture</button>` : ""}
        ${system.status === "active" ? '<span class="badge badge-green" style="font-size:13px;padding:8px 16px">Capture Active ✓</span>' : ""}
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
            Readiness: <strong class="${coverage.replay_readiness === "insufficient_context" ? "text-red" : "text-green"}">${esc(coverage.replay_readiness)}</strong>
          </div>
          <p style="font-size:12px;color:var(--muted);margin-top:8px">${esc(coverage.assessment || "")}</p>
        </div>
      ` : validationRuns.length > 0 ? `
        <p style="font-size:12px;color:var(--muted)">Last validation run: ${esc(validationRuns[validationRuns.length - 1].status)}</p>
      ` : `
        <div class="empty-state" style="border:1px dashed var(--border);padding:16px;border-radius:var(--radius)">
          <p>No validation runs yet. Run validation to check capture coverage. You need at least one connected capture source and field rules defined.</p>
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
    const runs = await apiGet("/v1/setup/ai-systems/" + systemId + "/validation-runs").catch(() => []);
    if (!runs.length) {
      notify("Run validation first before activating capture", "error");
      return;
    }
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
                return '<div class="evidence-node" onclick="event.stopPropagation();renderDrawer(\'Evidence: ' + esc(ev.kind) + '\', renderCodeBlock(' + JSON.stringify(JSON.stringify(ev, null, 2)) + '))"><span class="evidence-icon">' + icon + '</span><span class="evidence-kind">' + esc(ev.kind) + '</span><span class="evidence-summary">' + esc(typeof summary === "string" ? summary : JSON.stringify(summary).substring(0, 60)) + '</span></div>';
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
    const r = await apiPost("/v1/scenarios?vr_id=" + encodeURIComponent(vrId));
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
            ${i.can_issue_proof ? `<button class="btn btn-sm btn-green" onclick="runIncidentCertify('${i.incident_id}')">Issue Proof</button>` : ""}
            ${!i.can_issue_proof && i.mutation_result && !i.certificate ? `<button class="btn btn-sm btn-green" disabled title="${esc(i.issue_proof_reason || 'Fix verification must produce expected outcome')}">Issue Proof</button>` : ""}
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
    : [];

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
    return '<button class="incident-tab' + (active ? ' active' : '') + '" data-tab="' + label.toLowerCase() + '" onclick="switchIncidentTab(\'' + label.toLowerCase() + '\')">' + esc(label) + (count ? ' <span class="tab-badge">' + count + '</span>' : '') + '</button>';
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
    proofDetailHtml = '<div class="proof-pending"><strong>No certificate issued</strong><p>' + esc(proofError || "Issue Proof becomes available after a mitigated Fix Verification.") + '</p>' + (wf.issue_proof_next_action ? '<p style="margin-top:8px;font-size:12px;color:var(--muted)">Next: ' + esc(wf.issue_proof_next_action) + '</p>' : '') + '</div>';
  }

  var scenarioPromotionHtml = sourceVr
    ? '<p style="font-size:12px;color:var(--muted);margin-bottom:8px">Promote this verified failure as a reusable scenario so future release checks can detect the same decision regression.</p>' +
      (cert.certificate_id
        ? '<button class="btn btn-sm btn-outline" onclick="promoteToScenario(\'' + sourceVr.id + "','" + i.incident_id + '\')">Promote to Scenario</button>'
        : '<div class="proof-pending"><strong>Promotion pending proof</strong><p>Issue a proof certificate after a successful fix verification before promoting this incident to the scenario library.</p></div>')
    : '<div class="proof-pending"><strong>No source Verification Record</strong><p>Scenario promotion becomes available when this incident is linked to a Verification Record.</p></div>';

  var gateHtml = '<div class="gate-impact"><span class="gate-node gate-capture">Captured</span><span class="gate-line"></span><span class="gate-node ' + (i.replay_result ? "gate-fail" : "gate-muted") + '">' + (i.replay_result ? "Blocked before fix" : "Replay pending") + '</span><span class="gate-line"></span><span class="gate-node ' + (fixMitigated ? "gate-pass" : "gate-muted") + '">' + (fixMitigated ? "Pass after fix" : "Fix pending") + '</span><span class="gate-line"></span><span class="gate-node ' + (cert.certificate_id ? "gate-pass" : "gate-muted") + '">' + (cert.certificate_id ? "Proof attached" : "Gate not updated") + '</span></div><p class="section-sub" style="margin-top:8px">A promoted scenario can block a release when this known failure reappears. This is scenario-scoped evidence, not a general AI safety claim.</p>';

  c.innerHTML = [
    '<button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav(\'incidents\')">← Back to Incidents</button>',
    badgeDemo(),
    '<div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">',
    statusBadge(i.status),
    '<span style="font-size:13px;color:var(--muted)">ID: ' + esc(i.incident_id) + '</span>',
    '</div>',
    '<section>' + renderSection("Incident business summary", '<p class="section-sub" style="margin:0 0 12px">A captured AI decision is replayed from sealed evidence, compared with the original outcome, and verified again after the fix.</p><div class="incident-summary-v2">') + '</section>',
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
    '<div data-tab="evidence" style="display:' + (activeTab === "evidence" ? "block" : "none") + '">' + renderSection("Captured Evidence", (elements.length ? '<div class="evidence-table"><table><thead><tr><th>#</th><th>Kind</th><th>Source System</th><th>Summary</th></tr></thead><tbody>' + elements.map(function(e, idx) {
      var summary = "";
      if (e.payload) {
        if (e.payload.decision) summary = e.payload.decision;
        else if (e.payload.response && typeof e.payload.response === "object") summary = e.payload.response.status || JSON.stringify(e.payload.response).slice(0, 60);
        else if (e.payload.version) summary = e.payload.version;
        else if (e.payload.applicant_id) summary = e.payload.applicant_id;
        else summary = e.kind;
      }
      return '<tr onclick="event.stopPropagation();renderDrawer(\'Element ' + (idx + 1) + '\', renderCodeBlock(JSON.stringify(e, null, 2)))"><td>' + (idx + 1) + '</td><td><span class="badge badge-built">' + esc(e.kind) + '</span></td><td style="font-size:11px">' + esc(e.source_system || e.kind) + '</td><td style="font-size:11px">' + esc(typeof summary === "string" ? summary : JSON.stringify(summary).slice(0, 60)) + '</td></tr>';
    }).join("") + '</tbody></table></div>' : "No captured elements") + (sourceVr ? renderSection("Source Record", renderKV("Verification Record", '<span class="link" onclick="openVRDetail(\'' + sourceVr.id + '\')">' + sourceVr.id + '</span>') + renderKV("Replayability", statusBadge(sourceVr.replayability)) + renderKV("Label", sourceVr.current_label_id ? '<span class="link">' + esc(sourceVr.current_label_id) + '</span>' : "—")) : "")) + '</div>',
    '<div data-tab="replay" style="display:' + (activeTab === "replay" ? "block" : "none") + '">' + renderSection("Replay Execution Workspace", replayColumnsHtml) + (i.replay_result && i.replay_result.reason ? '<div class="error-state" style="margin-top:12px">Replay issue: ' + esc(i.replay_result.reason) + '</div>' : "") + renderSection("Decisions", renderKV("Original", '<span class="decision-pill decision-fail">' + esc(originalDecision) + '</span>') + renderKV("Replayed", '<span class="decision-pill ' + (replayedDecision === originalDecision ? "decision-fail" : "decision-neutral") + '">' + esc(replayedDecision || "Pending") + '</span>') + renderKV("Comparison", replayStatus === "pass" ? '<span style="color:var(--green);font-weight:800">Failure reproduced ✓</span>' : '<span style="color:var(--dim)">Pending</span>')) + '</div>',
    '<div data-tab="fix" style="display:' + (activeTab === "fix" ? "block" : "none") + '">' + fixDetailHtml + '</div>',
    '<div data-tab="proof" style="display:' + (activeTab === "proof" ? "block" : "none") + '">' + proofDetailHtml + renderSection("Scenario promotion", scenarioPromotionHtml) + '</div>',
    '<div data-tab="gate" style="display:' + (activeTab === "gate" ? "block" : "none") + '">' + gateHtml + '</div>',
    '<div data-tab="audit" style="display:' + (activeTab === "audit" ? "block" : "none") + '">' + renderSection("Chronological Audit Trail", custodyHtml || "No audit events recorded.") + '</div>',
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
  qa(".incident-tab-content > div[data-tab]").forEach(function(d) {
    d.style.display = d.dataset.tab === id ? "block" : "none";
  });
  qa(".incident-tab").forEach(function(b) {
    b.classList.toggle("active", b.dataset.tab === id);
  });
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
      ${renderKV("Schema Version", cert.schema_version || "pom-v1")}
      ${renderKV("Decision Workflow", p.workflow_title || cert.workflow_title || "Recorded AI decision workflow")}
      ${renderKV("Lifecycle", renderKV("Issued", cert.timestamp || cert.issued_at || "—") + renderKV("Status", "Certified"))}
      ${renderKV("Source Incident", `<span class="link" onclick="openIncidentDetail('${p.incident_id}')">${p.incident_id}</span>`)}
      ${renderKV("Source Verification Record", p.verification_record_id ? `<span class="link" onclick="openVRDetail('${p.verification_record_id}')">${p.verification_record_id}</span>` : "—")}
      ${renderKV("Source System", p.source_system_id || "—")}
      ${renderKV("Original AI Decision", `<span class="decision-pill decision-fail">${esc(p.original_decision || "—")}</span>`)}
      ${renderKV("Verified Fixed Outcome", `<span class="decision-pill decision-pass">${esc(p.mutated_decision || cert.mutated_decision || "—")}</span>`)}
      ${renderKV("Expected Outcome Provenance", cert.expected_correct_behavior || p.claim_scope || "Verified scenario outcome")}
      ${renderKV("Manifest", renderKV("Replay Method", cert.replay_method || "sealed cassette replay") + renderKV("Root Hash / Seal", cert.root_hash || "—") + renderKV("Schema Version", cert.schema_version || "pom-v1"))}
      ${renderKV("Conditions", 'This proof is valid for the recorded scenario under the conditions preserved in the sealed cassette. The fix outcome was verified against the expected correct behavior. The proof does not extend to inputs, configurations, or model versions outside the captured scope.')}
      ${renderKV("Provenance", renderKV("Replay Method", cert.replay_method || "sealed cassette replay") + renderKV("Root Hash / Seal", cert.root_hash || "—"))}
      ${renderKV("Signature Status", sig === true ? "✓ Valid" : sig === false ? "✗ Invalid" : "Unknown")}
      ${renderKV("Signing Algorithm", cert.signing_algorithm || "—")}
      ${renderKV("Claim Scope", p.claim_scope || cert.claim_scope || "Verified fix for this tested scenario under recorded conditions. Does not certify general AI safety.")}
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
  const active = scenarios.filter(s => s.state !== "retired");
  const retired = scenarios.filter(s => s.state === "retired");
  const libraryStats = buildScenarioLibraryStats(scenarios, candidates);
  c.innerHTML = `
    <div class="section-title">Scenario Library</div>
    <div class="section-sub">Promote verified incidents to reusable scenarios, test them against agent versions, and turn real failures into release gates.</div>
    <div class="stat-grid" style="margin-bottom:16px">
      ${[
        { value: libraryStats.total, label: "Library Scenarios", color: "var(--blue)" },
        { value: libraryStats.active, label: "Active", color: "var(--green)" },
        { value: libraryStats.candidates, label: "Candidates", color: "var(--amber)" },
        { value: libraryStats.ready, label: "Ready", color: "var(--purple)" },
        { value: libraryStats.blocked, label: "Blocked", color: "var(--red)" },
        { value: libraryStats.coverage, label: "Replay Coverage", color: "var(--accent)" },
      ].map(s => `
        <div class="stat">
          <div class="stat-val" style="color:${s.color}">${esc(String(s.value))}</div>
          <div class="stat-label">${esc(s.label)}</div>
        </div>
      `).join("")}
    </div>
    ${renderSection("Testing Playground", `
      <div class="int-card">
        <h4>Run the library against an agent version</h4>
        <p style="font-size:12px;color:var(--muted);margin-top:6px">Use the current agent version in the top bar to replay the active library and see which scenarios would block a release.</p>
        <div class="action-row" style="margin-top:12px">
          <button class="btn btn-sm" onclick="runScenarioSet(${JSON.stringify(active.map(s => s.id))})" ${active.length ? "" : "disabled"}>Run Active Library</button>
          <button class="btn btn-sm btn-outline" onclick="nav('readiness')">Open Readiness Policies</button>
        </div>
      </div>
    `)}
    ${renderSection("Scenario Intelligence", `
      <table>
        <thead><tr><th>Signal</th><th>Count</th><th>Meaning</th></tr></thead>
        <tbody>
          <tr><td>Reusable scenarios</td><td>${libraryStats.total}</td><td>Verified cases available as regression coverage</td></tr>
          <tr><td>Scenario candidates</td><td>${libraryStats.candidates}</td><td>Promotable records waiting for review</td></tr>
          <tr><td>Ready to gate</td><td>${libraryStats.ready}</td><td>Scenarios already trusted for readiness policies</td></tr>
          <tr><td>Needs attention</td><td>${libraryStats.blocked}</td><td>Scenarios with blocked sandbox or replay conditions</td></tr>
        </tbody>
      </table>
    `)}
    ${renderSection("Active Scenarios", active.length ? active.map(s => scenarioCard(s)).join("") : `<div class="empty-state compact"><h3>No scenarios in the library yet</h3><p>Promote a verified incident from the incident detail view, or seed demo data.</p></div>`)}
    ${retired.length ? renderSection("Retired Scenarios", retired.map(s => scenarioCard(s)).join("")) : ""}
    ${renderSection("Scenario Candidates", candidates.length ? candidates.filter(sc => sc.state === "candidate").map(sc => candidateCard(sc)).join("") : `<div class="empty-state compact"><h3>No candidates ready</h3><p>Candidates are created when you promote an incident that meets the readiness criteria.</p></div>`)}
  `;
}

function buildScenarioLibraryStats(scenarios, candidates) {
  const active = scenarios.filter(s => s.state === "active");
  const ready = scenarios.filter(s => s.required_sandbox_id && s.replayability !== "unknown").length;
  const blocked = scenarios.filter(s => s.replayability === "missing_context" || s.replayability === "requires_sandbox").length;
  const replayable = scenarios.filter(s => s.replayability === "replayable").length;
  const coverage = scenarios.length ? `${Math.round((replayable / scenarios.length) * 100)}%` : "0%";
  return {
    total: scenarios.length,
    active: active.length,
    candidates: candidates.filter(c => c.state === "candidate").length,
    ready,
    blocked,
    coverage,
  };
}

function scenarioCard(sc) {
  return `
    <div class="int-card">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <h4>${esc(sc.business_title)}</h4>
          <p style="font-size:12px;color:var(--muted)">Expected outcome: ${esc(sc.expected_outcome)} · Source VR: ${esc(sc.source_vr_id)}${sc.source_incident_id ? ` · Incident: ${esc(sc.source_incident_id)}` : ""}</p>
        </div>
        <span class="badge badge-${sc.state === "active" ? "built" : sc.state === "retired" ? "neutral" : "planned"}">${sc.state}</span>
      </div>
      <div style="font-size:12px;color:var(--muted);margin-top:8px">
        Replayability: ${statusBadge(sc.replayability)} ${Math.round((sc.replayability_score || 0) * 100)}% · Sandbox: ${sc.required_sandbox_id || "—"} · Last run: ${sc.last_run_status || "not_started"}
      </div>
      <div class="action-row" style="margin-top:12px">
        <button class="btn btn-sm" onclick="runScenarioSet(['${sc.id}'])">Run This Scenario</button>
        <button class="btn btn-sm btn-outline" onclick="openScenarioDetail('${sc.id}')">Detail</button>
        <button class="btn btn-sm btn-outline" onclick="copyScenarioExport('${sc.id}')">Export</button>
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
  const exportPayload = {
    id: s.id,
    business_title: s.business_title,
    source_vr_id: s.source_vr_id,
    source_incident_id: s.source_incident_id,
    source_system_id: s.source_system_id,
    expected_outcome: s.expected_outcome,
    replayability: s.replayability,
    replayability_score: s.replayability_score,
    required_sandbox_id: s.required_sandbox_id,
    evidence_refs: s.evidence_refs,
    state: s.state,
    last_run_status: s.last_run_status,
    created_at: s.created_at,
  };
  c.innerHTML = `
    <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="nav('scenarios')">← Back to Scenarios</button>
    <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
      <span class="badge badge-${s.state === "active" ? "built" : "planned"}">${s.state}</span>
      <span style="font-size:13px;color:var(--muted)">ID: ${s.id}</span>
    </div>
    ${renderSection("Summary", `
      ${renderKV("Business Title", s.business_title)}
      ${renderKV("Source V.R.", `<span class="link" onclick="openVRDetail('${s.source_vr_id}')">${s.source_vr_id}</span>`)}
      ${renderKV("Source Incident", s.source_incident_id ? `<span class="link" onclick="openIncidentDetail('${s.source_incident_id}')">${s.source_incident_id}</span>` : "—")}
      ${renderKV("Expected Outcome", s.expected_outcome)}
      ${renderKV("Replayability", statusBadge(s.replayability))}
      ${renderKV("Last Run Status", s.last_run_status || "not_started")}
      ${renderKV("Evidence Refs", s.evidence_refs && s.evidence_refs.length ? s.evidence_refs.join(", ") : "—")}
    `)}
    ${renderSection("Scenario Export", `
      <div class="int-card">
        ${renderCodeBlock(JSON.stringify(exportPayload, null, 2))}
        <div class="action-row" style="margin-top:12px">
          <button class="btn btn-sm btn-outline" onclick="copyScenarioExport('${s.id}')">Copy JSON</button>
        </div>
      </div>
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

async function copyScenarioExport(id) {
  try {
    const s = await apiGet("/v1/scenarios/" + id);
    const payload = JSON.stringify({
      id: s.id,
      business_title: s.business_title,
      source_vr_id: s.source_vr_id,
      source_incident_id: s.source_incident_id,
      source_system_id: s.source_system_id,
      expected_outcome: s.expected_outcome,
      replayability: s.replayability,
      replayability_score: s.replayability_score,
      required_sandbox_id: s.required_sandbox_id,
      evidence_refs: s.evidence_refs,
      state: s.state,
      last_run_status: s.last_run_status,
      created_at: s.created_at,
    }, null, 2);
    await copyToClipboard(payload);
    notify("Scenario JSON copied", "success");
  } catch (e) {
    notify("Export failed: " + e.message, "error");
  }
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

async function loadEnvironments() {
  try {
    const h = await apiGet("/v1/platform/home");
    const envs = h.environments || [];
    const sel = q("#env-select");
    sel.innerHTML = envs.map(e =>
      `<option value="${e.id}"${e.id === S.env ? " selected" : ""}>${e.name}</option>`
    ).join("");
    sel.disabled = false;
    if (S.view === "home") R();
  } catch (_) {
    // Silently fall back to demo-only.
  }
}

function init() {
  setupNav();
  const savedEnv = localStorage.getItem("np-env");
  if (savedEnv) {
    S.env = savedEnv;
  }
  const params = new URLSearchParams(location.search);
  if (params.get("view")) {
    S.view = params.get("view");
  }
  loadEnvironments();
  R();
}

document.addEventListener("DOMContentLoaded", init);
