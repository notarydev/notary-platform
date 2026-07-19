# Notary Platform — Consolidated Build Instructions (All 6 Batches)

## Before you start

Read the product spec at `docs/notary-platform-product-plan.md` for the full design.

This instruction file tells you exactly what code to write, in what order.

**Target:** `notary-platform` repo. Frontend lives in `static/app/index.html` (single-file SPA). Backend in `src/notary_platform/`.

**Running locally:**
```bash
cd /Users/hardyk/notary-platform
.venv/bin/pytest -q          # run tests (77 should pass)
.venv/bin/ruff check .       # lint
.venv/bin/mypy src           # typecheck
```

**SPA served at:** `http://localhost:8001/app` (when uvicorn runs on 8001)

---

# BATCH 1: Home + Demo Org Seed

## Step 1.1 — Seed 5 demo incidents

**File:** `src/notary_platform/api_server/routers/platform.py`

Add this endpoint at the bottom of the file:

```python
@router.post("/platform/seed-demo")
def seed_demo(_org: str = Depends(require_auth)) -> dict:
    """Create 5 demo incidents through the full proof-loop."""
    from notary_platform.demo_scenarios import SCENARIOS
    from notary_platform.replay_engine.replay import run_replay
    from notary_platform.replay_engine.mutation import run_mutation
    from notary_platform.certificates import generate_certificate
    from notary_platform.api_server.routers.incidents import _demo_agent_fn

    agent_fn = _demo_agent_fn
    if not agent_fn:
        return {"created": 0, "error": "no agent function registered"}

    created = []
    scenarios = {
        "inc-001-lending": ("lending-denial", "APPROVE", {"threshold": 620}, True),   # certify
        "inc-002-support": ("customer-service-handoff", "ROUTE_TO_HUMAN", {"timeout": 60}, True),  # certify
        "inc-003-prior-auth": ("prior-authorization", "APPROVE", {"days": 14}, False),  # mitigated only
        "inc-004-hiring": ("hiring-screen", "APPROVE", {}, False),  # replayed only
        "inc-005-complaint": ("complaint-escalation", "", {}, False),  # ingested only
    }

    for iid, (scenario_id, expected, fix_config, certify) in scenarios.items():
        scenario = SCENARIOS.get(scenario_id)
        if not scenario:
            continue
        from notary_platform.demo_scenarios import build_snapshot
        from notary_platform.models import Incident
        snap = build_snapshot(scenario)[1]  # (name, snapshot_dict)
        inc = storage.create_incident(snap, org_id=_org)
        inc._record_custody("ingested", actor="system", detail=f"demo seed: {scenario_id}")
        storage.update_incident(inc)
        storage.persist_evidence(inc.incident_id, "snapshot", snap)

        # Replay
        if agent_fn:
            run_replay(inc, snap, agent_fn)
            storage.update_incident(inc)

        # Mutation (if expected set)
        if expected and agent_fn:
            result = run_mutation(snap, agent_fn, fix_config, expected_correct_behavior=expected, original_result=inc.replay_result)
            inc.mutation_result = result
            if result.get("mitigated"):
                inc.status = IncidentStatus("mitigated")
            storage.update_incident(inc)

        # Certify (if flagged)
        if certify and inc.mutation_result:
            cert = generate_certificate(
                incident_id=inc.incident_id,
                root_hash=inc.snapshot_summary.get("root_hash", ""),
                integrity_status="verified",
                replay_result=inc.replay_result,
                original_decision=inc.mutation_result.get("original_decision"),
                mutated_decision=inc.mutation_result.get("mutated_decision"),
                fix_config=inc.mutation_result.get("fix_config", {}),
                expected_correct_behavior=inc.mutation_result.get("expected_correct_behavior", ""),
                timestamp=inc.snapshot_summary.get("timestamp", ""),
            )
            inc.certificate = cert
            inc.status = IncidentStatus("certified")
            storage.store_certificate(inc.incident_id, cert)
            storage.update_incident(inc)

        created.append(inc.incident_id)

    return {"created": len(created), "incident_ids": created}
```

You need these imports at the top of platform.py (add if missing):
```python
from notary_platform.models import IncidentStatus
```

**Verify:** `curl http://localhost:8001/v1/platform/seed-demo -X POST` returns `{"created": 5, ...}`.

## Step 1.2 — Extend Home API

**File:** `src/notary_platform/api_server/routers/platform.py`

Replace the existing `get_home` function with:

```python
@router.get("/platform/home")
def get_home(
    environment_id: str = Query("env:demo"),
    _org: str = Depends(require_auth),
) -> dict:
    """Return Home overview stats for the given environment."""
    agents = [a for a in _SEED["agents"] if a.environment_id == environment_id]
    systems = [s for s in _SEED["systems"] if s.environment_id == environment_id]
    incidents = storage.list_incidents(org_id=_org)
    incident_count = len(incidents)
    replay_ready = sum(1 for i in incidents if i.replay_result)
    fixes_verified = sum(1 for i in incidents if i.status.value == "mitigated")
    proofs_issued = sum(1 for i in incidents if i.status.value == "certified")
    pending_replay = sum(1 for i in incidents if i.status.value == "ingested" and not i.replay_result)
    pending_verification = sum(1 for i in incidents if i.status.value == "replayed" and i.status.value != "mitigated")

    # Setup health
    connected_agents = sum(1 for a in agents if a.sdk_status == "connected")
    connected_systems = sum(1 for s in systems if s.status == "connected")
    setup_health = {
        "sdk_installed": connected_agents > 0,
        "agents_instrumented": connected_agents,
        "systems_connected": connected_systems,
        "systems_total": len(systems),
        "capture_policies": len(_SEED["policies"]),
        "incidents_collected": incident_count,
        "proofs_issued": proofs_issued,
    }

    # Active queues
    queues = {
        "needs_replay": pending_replay,
        "needs_verification": pending_verification,
        "proofs_ready": fixes_verified - proofs_issued,
    }

    # Recent proofs
    recent_proofs = []
    for inc in incidents:
        if inc.certificate and inc.status.value == "certified":
            recent_proofs.append({
                "incident_id": inc.incident_id,
                "agent": "Lending Decision Agent" if "lending" in inc.incident_id else "Support Handoff Agent",
                "status": "certified",
                "date": inc.certificate.get("timestamp", ""),
            })
    recent_proofs = recent_proofs[:5]

    # Next action (priority order)
    actions = [i for i in incidents if not i.replay_result and i.status.value == "ingested"]
    if not actions:
        actions = [i for i in incidents if i.status.value == "replayed" and not inc.mutation_result if hasattr(i, 'mutation_result')]
    if not actions:
        actions = [i for i in incidents if i.status.value == "mitigated" and not i.certificate]
    next_action = {
        "action": "replay" if actions and not (actions[0].replay_result) else "verify" if actions else "proof",
        "incident_id": actions[0].incident_id if actions else None,
        "label": f"Replay {actions[0].incident_id}" if (actions and not actions[0].replay_result) else f"Verify fix for {actions[0].incident_id}" if actions else "All caught up",
    } if actions else None

    return {
        "org_id": _DEMO_ORG.id,
        "environment_id": environment_id,
        "agent_count": len(agents),
        "system_count": len(systems),
        "incident_count": incident_count,
        "replay_ready": replay_ready,
        "fixes_verified": fixes_verified,
        "proofs_issued": proofs_issued,
        "scenario_count": sum(a.scenario_count for a in agents),
        "pending_replay": pending_replay,
        "pending_verification": pending_verification,
        "pending_proof": fixes_verified - proofs_issued,
        "setup_health": setup_health,
        "queues": queues,
        "recent_proofs": recent_proofs,
        "next_action": next_action,
        "is_demo": True,
    }
```

**Verify:** `curl http://localhost:8001/v1/platform/home?environment_id=env:demo` returns all new fields.

---

# BATCH 2: Frontend Rebuild — Home, States, Cross-Cutting

The entire Notary Platform SPA lives in ONE file: `static/app/index.html`

Replace the entire content of this file with the SPA below. It covers:
- Home page with all sections
- Incidents queue with actions
- Incident Investigation module
- Agents table with detail drawer
- Systems, Capture, Onboarding (simpler versions)
- Proofs, Scenarios, Governance, Settings (scaffolds/placeholders)
- All cross-cutting states: loading, empty, error, disabled, demo markings
- Environment switching

## Step 2.1 — Write the SPA

**File:** `static/app/index.html` — replace entire content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Notary Platform</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #050812; --surface: #0d1320; --border: #1f2a3d;
    --text: #e5eefc; --muted: #91a4c0; --dim: #5b6b86;
    --accent: #3b82d4; --green: #22c55e; --amber: #f59e0b;
    --red: #ef4444; --purple: #7c5cd8; --radius: 10px;
  }
  body { font-family: -apple-system, "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--text); height: 100vh; display: flex; }
  /* Sidebar */
  .side { width: 220px; min-width: 220px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; }
  .side-brand { padding: 16px; font-weight: 800; font-size: 15px; color: var(--text); border-bottom: 1px solid var(--border); letter-spacing: 0.3px; }
  .side-brand span { color: var(--accent); }
  .side-nav { flex: 1; overflow-y: auto; padding: 8px; }
  .nav-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 8px; font-size: 13px; font-weight: 600; color: var(--muted); cursor: pointer; transition: .15s; margin-bottom: 2px; border: none; background: none; width: 100%; text-align: left; }
  .nav-item:hover { background: rgba(59,130,212,.1); color: var(--text); }
  .nav-item.active { background: rgba(59,130,212,.18); color: var(--accent); }
  .nav-env { padding: 8px 12px; margin-top: 8px; font-size: 10px; text-transform: uppercase; color: var(--dim); font-weight: 700; letter-spacing: 0.5px; }
  /* Main */
  .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
  .topbar { display: flex; align-items: center; gap: 12px; padding: 10px 24px; border-bottom: 1px solid var(--border); background: var(--surface); flex-shrink: 0; flex-wrap: wrap; }
  .topbar h1 { font-size: 16px; font-weight: 700; white-space: nowrap; }
  .env-select { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); color: var(--muted); cursor: pointer; }
  .env-select option { background: var(--surface); color: var(--text); }
  .demo-badge { font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 999px; background: rgba(245,158,11,.12); color: var(--amber); border: 1px solid rgba(245,158,11,.3); text-transform: uppercase; }
  .demo-banner { padding: 8px 16px; background: rgba(245,158,11,.08); border-bottom: 1px solid rgba(245,158,11,.2); color: var(--amber); font-size: 12px; font-weight: 600; text-align: center; flex-shrink: 0; }
  .content { flex: 1; overflow-y: auto; padding: 24px; }
  /* Cards */
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .stat { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px; position: relative; }
  .stat-val { font-size: 24px; font-weight: 800; line-height: 1; }
  .stat-label { font-size: 11px; color: var(--muted); margin-top: 4px; font-weight: 600; }
  .stat-icon { font-size: 14px; position: absolute; top: 12px; right: 14px; }
  .section-title { font-size: 13px; font-weight: 800; margin: 20px 0 10px; color: var(--text); text-transform: uppercase; letter-spacing: 0.5px; }
  /* Queue chips */
  .queue-row { display: flex; gap: 12px; margin-bottom: 24px; }
  .queue-chip { flex: 1; padding: 12px 16px; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface); cursor: pointer; transition: .15s; display: flex; align-items: center; gap: 10px; }
  .queue-chip:hover { border-color: var(--accent); }
  .queue-count { font-size: 22px; font-weight: 800; }
  .queue-label { font-size: 12px; color: var(--muted); font-weight: 600; }
  /* Table */
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; font-size: 10px; font-weight: 800; text-transform: uppercase; color: var(--dim); padding: 8px 12px; border-bottom: 1px solid var(--border); letter-spacing: 0.5px; position: sticky; top: 0; background: var(--bg); }
  td { padding: 10px 12px; border-bottom: 1px solid rgba(31,42,61,.5); color: var(--muted); }
  td:first-child { font-weight: 600; color: var(--text); }
  tr { cursor: pointer; transition: .1s; }
  tr:hover { background: rgba(59,130,212,.06); }
  /* Badges */
  .badge { font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 999px; text-transform: uppercase; display: inline-block; }
  .badge-ingested { background: rgba(156,163,175,.12); color: #9ca3af; border: 1px solid rgba(156,163,175,.3); }
  .badge-replayed { background: rgba(59,130,212,.12); color: #3b82d4; border: 1px solid rgba(59,130,212,.3); }
  .badge-mitigated { background: rgba(245,158,11,.12); color: #f59e0b; border: 1px solid rgba(245,158,11,.3); }
  .badge-certified { background: rgba(34,197,94,.12); color: #22c55e; border: 1px solid rgba(34,197,94,.3); }
  .badge-demo { background: rgba(245,158,11,.12); color: #f59e0b; border: 1px solid rgba(245,158,11,.3); }
  .badge-planned { background: rgba(107,114,128,.12); color: #6b7280; border: 1px solid rgba(107,114,128,.3); }
  .status-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; }
  .status-connected { background: var(--green); } .status-disconnected { background: var(--red); }
  .status-stale { background: var(--amber); } .status-planned { background: var(--dim); }
  .status-not_installed { background: var(--dim); } .status-unknown { background: var(--dim); }
  /* Buttons */
  .btn { font-size: 12px; font-weight: 700; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--accent); background: var(--accent); color: #fff; cursor: pointer; transition: .15s; white-space: nowrap; }
  .btn:hover { opacity: .85; }
  .btn-sm { font-size: 11px; padding: 4px 10px; }
  .btn-outline { background: transparent; color: var(--accent); }
  .btn-disabled { opacity: .4; cursor: not-allowed; pointer-events: none; }
  .btn-disabled:hover { opacity: .4; }
  .btn-danger { background: var(--red); border-color: var(--red); }
  .action-row { display: flex; gap: 8px; flex-wrap: wrap; }
  /* Modal/overlay */
  .modal-overlay { position: fixed; inset: 0; background: rgba(5,8,18,.6); display: flex; align-items: flex-start; justify-content: center; z-index: 200; padding-top: 60px; }
  .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; width: 640px; max-width: 95vw; max-height: 85vh; overflow-y: auto; box-shadow: 0 16px 48px rgba(0,0,0,.4); }
  .modal-header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
  .modal-header h2 { font-size: 15px; font-weight: 700; }
  .modal-close { background: none; border: 1px solid var(--border); color: var(--muted); font-size: 14px; padding: 4px 10px; border-radius: 6px; cursor: pointer; }
  .modal-body { padding: 16px 20px; }
  .modal-body section { margin-bottom: 20px; }
  .modal-body h3 { font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; color: var(--dim); margin-bottom: 8px; }
  .modal-body p, .modal-body li { font-size: 12.5px; color: var(--muted); line-height: 1.6; }
  .modal-body .kv { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(31,42,61,.4); }
  .modal-body .kv-label { color: var(--dim); font-size: 11px; font-weight: 700; text-transform: uppercase; }
  .modal-body .kv-value { color: var(--text); font-size: 12px; font-weight: 600; }
  /* Detail drawer (side panel) */
  .drawer-overlay { position: fixed; inset: 0; background: rgba(5,8,18,.5); display: flex; align-items: stretch; justify-content: flex-end; z-index: 200; }
  .drawer { background: rgba(13,19,32,.98); width: 460px; max-width: 95vw; height: 100%; overflow-y: auto; border-left: 1px solid var(--border); box-shadow: -8px 0 24px rgba(0,0,0,.35); }
  .drawer-header { padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; background: rgba(13,19,32,.98); z-index: 1; }
  .drawer-body { padding: 14px 18px; }
  /* States */
  .skeleton { background: rgba(31,42,61,.5); border-radius: var(--radius); animation: sk-pulse 1.5s infinite; }
  @keyframes sk-pulse { 0%,100% { opacity: .4; } 50% { opacity: .7; } }
  .empty-state { text-align: center; padding: 48px 24px; }
  .empty-state h3 { font-size: 15px; font-weight: 700; margin: 12px 0 8px; }
  .empty-state p { font-size: 13px; color: var(--muted); margin-bottom: 16px; }
  .error-state { text-align: center; padding: 48px 24px; }
  .error-state p { font-size: 13px; color: var(--red); margin: 12px 0; }
  /* Incident filter pills */
  .filter-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
  .filter-pill { font-size: 11px; font-weight: 700; padding: 4px 12px; border-radius: 999px; border: 1px solid var(--border); background: transparent; color: var(--muted); cursor: pointer; transition: .15s; }
  .filter-pill.active { background: rgba(59,130,212,.18); color: var(--accent); border-color: var(--accent); }
  .hidden { display: none !important; }
</style>
</head>
<body>

<div class="side">
  <div class="side-brand">◈ Notary <span>Platform</span></div>
  <div class="side-nav">
    <button class="nav-item active" data-view="home">⌂ Home</button>
    <button class="nav-item" data-view="onboarding">▶ Onboarding</button>
    <button class="nav-item" data-view="agents">◆ Agents</button>
    <button class="nav-item" data-view="systems">◎ Systems</button>
    <button class="nav-item" data-view="capture">◈ Capture</button>
    <button class="nav-item" data-view="incidents">⚠ Incidents</button>
    <button class="nav-item" data-view="replay">↻ Replay & Verify</button>
    <button class="nav-item" data-view="proofs">✓ Proofs</button>
    <button class="nav-item" data-view="scenarios">▤ Scenarios</button>
    <button class="nav-item" data-view="governance">⚖ Governance</button>
    <button class="nav-item" data-view="settings">⚙ Settings</button>
  </div>
</div>

<div class="main">
  <div class="topbar">
    <h1 id="view-title">Home</h1>
    <select class="env-select" id="env-select" onchange="switchEnv(this.value)">
      <option value="env:demo">Demo</option>
      <option value="env:staging">Staging</option>
      <option value="env:production">Production</option>
    </select>
    <span class="demo-badge hidden" id="global-demo-badge">DEMO</span>
    <span style="margin-left:auto;font-size:11px;color:var(--dim)" id="org-name"></span>
  </div>
  <div class="demo-banner hidden" id="demo-banner">Demo data — not production. Seed demo incidents to explore.</div>
  <div class="content" id="content"><div class="skeleton" style="height:200px"></div></div>
</div>

<div id="modal-container"></div>
<div id="drawer-container"></div>

<script>
// ── State ──
const API = "/v1/platform";
let state = { env: "env:demo", view: "home", data: {} };

// ── Helpers ──
function qs(s) { return document.querySelector(s); }
function qsa(s) { return document.querySelectorAll(s); }
async function api(path) { const r = await fetch(`/v1${path}`); if (!r.ok) throw new Error(r.status); return r.json(); }
async function apiPost(path, body) { const r = await fetch(`/v1${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body||{}) }); if (!r.ok) throw new Error(r.status); return r.json(); }
function envUrl(path) { return `${path}?environment_id=${state.env}`; }

function badge(status) {
  const cls = "badge badge-" + status;
  const labels = { ingested: "Ingested", replayed: "Replayed", mitigated: "Mitigated", certified: "Certified" };
  return `<span class="${cls}">${labels[status] || status}</span>`;
}
function demoBadge() { return state.env === "env:demo" ? '<span class="badge badge-demo">DEMO</span>' : ''; }
function planBadge() { return '<span class="badge badge-planned">PLANNED</span>'; }

function formatDate(ts) {
  if (!ts) return "—";
  try { const d = new Date(ts); return d.toLocaleDateString(); } catch { return ts; }
}

function skeleton(h) { return `<div class="skeleton" style="height:${h}px;margin-bottom:12px"></div>`; }
function empty(title, msg, btnLabel, btnAction) {
  return `<div class="empty-state"><h3>${title}</h3><p>${msg}</p>${btnLabel ? `<button class="btn" onclick="${btnAction}">${btnLabel}</button>` : ''}</div>`;
}
function error(msg) { return `<div class="error-state"><p>⚠ ${msg}</p><button class="btn" onclick="render()">Retry</button></div>`; }

// ── Router ──
qsa(".nav-item[data-view]").forEach(el => {
  el.addEventListener("click", () => {
    qsa(".nav-item[data-view]").forEach(x => x.classList.remove("active"));
    el.classList.add("active");
    state.view = el.getAttribute("data-view");
    render();
  });
});

function switchEnv(envId) {
  state.env = envId;
  localStorage.setItem("np-env", envId);
  render();
}

// Init
const savedEnv = localStorage.getItem("np-env");
if (savedEnv) { state.env = savedEnv; qs("#env-select").value = savedEnv; }

// ── Render dispatcher ──
async function render() {
  const c = qs("#content");
  const title = state.view.replace(/-/g, " ").replace(/\b\w/g, x => x.toUpperCase());
  qs("#view-title").textContent = title;
  qs("#demo-banner").classList.toggle("hidden", state.env !== "env:demo");
  qs("#global-demo-badge").classList.toggle("hidden", state.env !== "env:demo");

  c.innerHTML = skeleton(100) + skeleton(100) + skeleton(60);
  try {
    const home = await api(envUrl("/platform/home"));
    state.data.home = home;
    qs("#org-name").textContent = "Acme Assurance Demo";

    if (state.view === "home") renderHome(c, home);
    else if (state.view === "onboarding") renderOnboarding(c);
    else if (state.view === "agents") await renderAgents(c);
    else if (state.view === "systems") await renderSystems(c);
    else if (state.view === "capture") await renderCapture(c);
    else if (state.view === "incidents") await renderIncidents(c);
    else if (state.view === "replay") renderReplay(c);
    else if (state.view === "proofs") await renderProofs(c);
    else if (state.view === "scenarios") renderScenarios(c);
    else if (state.view === "governance") renderGovernance(c);
    else if (state.view === "settings") renderSettings(c);
    else if (state.view === "investigation") renderInvestigation(c);
    else c.innerHTML = error("Unknown view: " + state.view);
  } catch(e) {
    c.innerHTML = error("Could not load. Is the API running?");
  }
}

// ── HOME ──
function renderHome(c, home) {
  const h = home || state.data.home;
  const sh = h.setup_health || {};
  const q = h.queues || {};
  const proofs = h.recent_proofs || [];
  const na = h.next_action;

  const stats = [
    { color: "var(--green)", icon: "✓", val: sh.sdk_installed ? "Yes" : "No", label: "SDK Installed" },
    { color: "var(--accent)", icon: "◆", val: sh.agents_instrumented, label: "Agents" },
    { color: "var(--purple)", icon: "◎", val: `${sh.systems_connected}/${sh.systems_total}`, label: "Systems Connected" },
    { color: "var(--blue)", icon: "◈", val: sh.capture_policies, label: "Policies" },
    { color: "var(--amber)", icon: "⚠", val: sh.incidents_collected, label: "Incidents" },
    { color: "var(--green)", icon: "✓", val: sh.proofs_issued, label: "Proofs Issued" },
  ];

  c.innerHTML = `
    ${demoBadge() ? `<div style="margin-bottom:16px">${demoBadge()} Demo data — not production</div>` : ''}
    <div class="stat-grid">
      ${stats.map(s => `
        <div class="stat">
          <div class="stat-icon" style="color:${s.color}">${s.icon}</div>
          <div class="stat-val" style="color:${s.color}">${s.val}</div>
          <div class="stat-label">${s.label}</div>
        </div>`).join("")}
    </div>

    <div class="section-title">Active Queues</div>
    <div class="queue-row">
      <div class="queue-chip" onclick="navigate('incidents?filter=ingested')" style="border-left:3px solid var(--red)">
        <div class="queue-count" style="color:var(--red)">${q.needs_replay||0}</div>
        <div class="queue-label">Need replay</div>
      </div>
      <div class="queue-chip" onclick="navigate('incidents?filter=replayed')" style="border-left:3px solid var(--amber)">
        <div class="queue-count" style="color:var(--amber)">${q.needs_verification||0}</div>
        <div class="queue-label">Need verification</div>
      </div>
      <div class="queue-chip" onclick="navigate('incidents?filter=mitigated')" style="border-left:3px solid var(--green)">
        <div class="queue-count" style="color:var(--green)">${q.proofs_ready||0}</div>
        <div class="queue-label">Proofs ready</div>
      </div>
    </div>

    ${proofs.length > 0 ? `
      <div class="section-title">Recent Proofs</div>
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden">
        ${proofs.map(p => `
          <div style="padding:10px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;font-size:12px;cursor:pointer" onclick="navigate('proofs')">
            <span style="font-weight:700;color:var(--text)">${p.incident_id}</span>
            <span style="color:var(--muted)">${p.agent}</span>
            ${badge('certified')}
            <span style="color:var(--dim);margin-left:auto">${formatDate(p.date)}</span>
          </div>`).join("")}
      </div>
    ` : ''}

    ${na ? `
      <div class="section-title">Next Action</div>
      <div class="stat" style="cursor:pointer;border:2px solid var(--accent)" onclick="navigate('incidents')">
        <div style="font-size:14px;font-weight:700;color:var(--accent)">${na.label}</div>
        <div class="stat-label" style="margin-top:4px">Click to open incidents</div>
      </div>
    ` : ''}
  `;
}

function navigate(view) {
  state.view = view.replace(/\?.*/, "");
  qsa(".nav-item[data-view]").forEach(x => x.classList.remove("active"));
  const btn = qs(`.nav-item[data-view="${state.view}"]`);
  if (btn) btn.classList.add("active");
  render();
}

// ── ONBOARDING ──
function renderOnboarding(c) {
  const steps = [
    { n: 1, title: "Install SDK", desc: "Run this in your agent environment:", code: "pip install notary-sdk" },
    { n: 2, title: "Instrument an Agent", desc: "Wrap your decision function:", code: '@notary.capture\ndef my_agent(req):\n    return decision' },
    { n: 3, title: "Send Test Capture", action: "Run Test Capture", onclick: "runTestCapture()" },
    { n: 4, title: "Connect Systems", desc: "Configure your external connections.", link: "systems", linkLabel: "Go to Systems →" },
    { n: 5, title: "Create Capture Policy", desc: "Define what gets captured.", link: "capture", linkLabel: "Go to Capture →" },
    { n: 6, title: "View First Incident", desc: "Results appear here after capture.", link: "incidents", linkLabel: "Go to Incidents →" },
  ];
  c.innerHTML = steps.map(s => `
    <div class="stat" style="margin-bottom:12px;display:flex;gap:14px;align-items:flex-start">
      <div style="width:28px;height:28px;border-radius:50%;border:2px solid var(--accent);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:var(--accent);flex-shrink:0">${s.n}</div>
      <div style="flex:1">
        <div style="font-size:14px;font-weight:700"">${s.title}</div>
        <div style="font-size:12px;color:var(--muted);margin-top:4px">${s.desc||''}</div>
        ${s.code ? `<pre style="background:#111827;color:var(--green);padding:8px 12px;border-radius:6px;font-size:11px;margin-top:8px;overflow-x:auto">${s.code}</pre>` : ''}
        ${s.action ? `<button class="btn btn-sm" style="margin-top:8px" onclick="${s.onclick}">${s.action}</button>` : ''}
        ${s.link ? `<a href="#" style="color:var(--accent);font-size:12px;font-weight:600;display:inline-block;margin-top:8px" onclick="navigate('${s.link}');return false">${s.linkLabel}</a>` : ''}
      </div>
    </div>
  `).join("");
}

async function runTestCapture() {
  const c = qs("#content");
  c.innerHTML = '<div class="skeleton" style="height:40px"></div><p style="color:var(--muted);font-size:13px">Running test capture...</p>';
  try {
    await apiPost("/platform/seed-demo");
    c.innerHTML = '<div style="text-align:center;padding:32px"><div style="font-size:48px">✓</div><h3 style="color:var(--green);margin-top:12px">Capture successful!</h3><p style="color:var(--muted);font-size:13px">5 demo incidents created. Check the Incidents page.</p><button class="btn" style="margin-top:12px" onclick="navigate(\'incidents\')">View Incidents</button></div>';
  } catch(e) {
    c.innerHTML = error("Capture failed. Is the API running?");
  }
}

// ── AGENTS ──
async function renderAgents(c) {
  try {
    const agents = await api(envUrl("/platform/org/agents"));
    if (!agents.length) { c.innerHTML = empty("No Agents", "Register an agent to get started.", "Register Agent", "alert('Coming soon')"); return; }
    c.innerHTML = `
      <div style="margin-bottom:16px"><button class="btn btn-sm" onclick="alert('Coming soon')">+ Register Agent</button></div>
      <table>
        <thead><tr><th>Name</th><th>Risk</th><th>SDK</th><th>Version</th><th>Last Seen</th><th>Incidents</th><th>Scenarios</th></tr></thead>
        <tbody>${agents.map(a => `
          <tr onclick="openAgentDrawer('${a.id}')">
            <td>${demoBadge()} ${a.name}</td>
            <td>${a.risk_tier}</td>
            <td><span class="status-dot status-${a.sdk_status}"></span>${a.sdk_status.replace(/_/g,' ')}</td>
            <td>${a.sdk_version||'—'}</td>
            <td>${a.last_seen ? formatDate(a.last_seen) : '—'}</td>
            <td>${a.scenario_count||0}</td>
            <td>${a.scenario_count||0}</td>
          </tr>`).join("")}</tbody>
      </table>`;
  } catch(e) { c.innerHTML = error("Could not load agents."); }
}

function openAgentDrawer(id) {
  const agents = state.data._agents || [];
  const a = agents.find(x => x.id === id);
  if (!a) return;
  const drawer = document.getElementById("drawer-container");
  drawer.innerHTML = `
    <div class="drawer-overlay" onclick="this.parentElement.innerHTML=''">
      <div class="drawer" onclick="event.stopPropagation()">
        <div class="drawer-header">
          <span style="font-weight:800;font-size:13px">${a.name}</span>
          <button class="modal-close" onclick="this.closest('.drawer-overlay').remove()">✕</button>
        </div>
        <div class="drawer-body">
          ${demoBadge()}
          <div class="kv"><span class="kv-label">Risk Tier</span><span class="kv-value">${a.risk_tier}</span></div>
          <div class="kv"><span class="kv-label">SDK Status</span><span class="kv-value"><span class="status-dot status-${a.sdk_status}"></span>${a.sdk_status.replace(/_/g,' ')}</span></div>
          <div class="kv"><span class="kv-label">Version</span><span class="kv-value">${a.sdk_version||'—'}</span></div>
          <div class="kv"><span class="kv-label">Last Seen</span><span class="kv-value">${a.last_seen ? formatDate(a.last_seen) : '—'}</span></div>
          <div style="margin-top:16px" class="action-row">
            <button class="btn btn-sm" disabled>Setup SDK</button>
            <button class="btn btn-sm btn-outline" onclick="navigate('incidents')">View Incidents</button>
          </div>
        </div>
      </div>
    </div>`;
}

// ── SYSTEMS ──
async function renderSystems(c) {
  try {
    const systems = await api(envUrl("/platform/org/systems"));
    if (!systems.length) { c.innerHTML = empty("No Systems", "Connect an external system to get started."); return; }
    c.innerHTML = `
      <table>
        <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Capability</th></tr></thead>
        <tbody>${systems.map(s => `
          <tr>
            <td>${demoBadge()} ${s.name}</td>
            <td>${s.kind}</td>
            <td><span class="status-dot status-${s.status}"></span>${s.status}</td>
            <td>${s.capability||'—'}</td>
          </tr>`).join("")}</tbody>
      </table>`;
  } catch(e) { c.innerHTML = error("Could not load systems."); }
}

// ── CAPTURE ──
async function renderCapture(c) {
  try {
    const policies = await api(envUrl("/platform/org/policies"));
    if (!policies.length) { c.innerHTML = empty("No Policies", "Create a capture policy to define what gets recorded."); return; }
    c.innerHTML = `
      <table>
        <thead><tr><th>Policy</th><th>Coverage</th><th>Status</th><th>Agent</th></tr></thead>
        <tbody>${policies.map(p => `
          <tr>
            <td>${demoBadge()} ${p.name}</td>
            <td>${p.coverage}</td>
            <td>${p.status}</td>
            <td>${p.agent_id||'—'}</td>
          </tr>`).join("")}</tbody>
      </table>`;
  } catch(e) { c.innerHTML = error("Could not load policies."); }
}

// ── INCIDENTS ──
async function renderIncidents(c) {
  try {
    const incidents = await api("/v1/incidents");
    state.data.incidents = incidents;
    if (!incidents.length) {
      c.innerHTML = empty("No Incidents", "Incidents appear when Notary captures a decision.", "Seed Demo Data", "seedDemo()");
      return;
    }
    c.innerHTML = `
      <div class="filter-pills">
        <button class="filter-pill active" onclick="filterIncidents('all',this)">All (${incidents.length})</button>
        <button class="filter-pill" onclick="filterIncidents('ingested',this)">Ingested</button>
        <button class="filter-pill" onclick="filterIncidents('replayed',this)">Replayed</button>
        <button class="filter-pill" onclick="filterIncidents('mitigated',this)">Mitigated</button>
        <button class="filter-pill" onclick="filterIncidents('certified',this)">Certified</button>
      </div>
      <div style="margin-bottom:12px">
        <button class="btn btn-sm" onclick="seedDemo()">Seed Demo Data</button>
      </div>
      <table id="incidents-table">
        <thead><tr><th>ID</th><th>Status</th><th>Replay</th><th>Mutation</th><th>Certificate</th><th>Actions</th></tr></thead>
        <tbody id="incidents-body">
          ${incidents.map(inc => incidentRow(inc)).join("")}
        </tbody>
      </table>`;
  } catch(e) { c.innerHTML = error("Could not load incidents."); }
}

function incidentRow(inc) {
  const st = inc.status;
  const hasReplay = inc.replay_result && Object.keys(inc.replay_result).length > 0;
  const hasMutation = inc.mutation_result && Object.keys(inc.mutation_result).length > 0;
  const hasCert = inc.certificate && Object.keys(inc.certificate).length > 0;
  return `<tr class="inc-row" data-status="${st}">
    <td>${demoBadge()} <span style="cursor:pointer;text-decoration:underline" onclick="openInvestigation('${inc.incident_id}')">${inc.incident_id}</span></td>
    <td>${badge(st)}</td>
    <td>${hasReplay ? '✓' : '—'}</td>
    <td>${hasMutation ? '✓' : '—'}</td>
    <td>${hasCert ? '✓' : '—'}</td>
    <td class="action-row">
      ${!hasReplay ? `<button class="btn btn-sm btn-outline" onclick="replayIncident('${inc.incident_id}')">Replay</button>` : ''}
      ${hasReplay && !hasMutation ? `<button class="btn btn-sm btn-outline" onclick="verifyFix('${inc.incident_id}')">Verify Fix</button>` : ''}
      ${hasMutation && !hasCert ? `<button class="btn btn-sm" onclick="issueProof('${inc.incident_id}')">Issue Proof</button>` : ''}
      <button class="btn btn-sm btn-outline" onclick="openInvestigation('${inc.incident_id}')">Investigate</button>
    </td>
  </tr>`;
}

function filterIncidents(status, btn) {
  qsa(".filter-pill").forEach(p => p.classList.remove("active"));
  btn.classList.add("active");
  qsa(".inc-row").forEach(row => {
    row.classList.toggle("hidden", status !== "all" && row.dataset.status !== status);
  });
}

async function replayIncident(id) {
  try { await apiPost(`/v1/incidents/${id}/replay`); render(); } catch(e) { alert("Replay failed: " + e.message); }
}
async function verifyFix(id) {
  try { await apiPost(`/v1/incidents/${id}/mutation-tests`, { fix_config: { threshold: 620 }, expected_correct_behavior: "APPROVE" }); render(); } catch(e) { alert("Fix verification failed: " + e.message); }
}
async function issueProof(id) {
  try { await apiPost(`/v1/incidents/${id}/certificates`); render(); } catch(e) { alert("Proof issuance failed: " + e.message); }
}
async function seedDemo() {
  const c = qs("#content");
  c.innerHTML = '<div class="skeleton" style="height:40px"></div><p>Seeding demo data...</p>';
  try { await apiPost("/platform/seed-demo"); render(); } catch(e) { c.innerHTML = error("Seed failed."); }
}

// ── INVESTIGATION ──
async function openInvestigation(id) {
  state.view = "investigation";
  state.investigationId = id;
  const c = qs("#content");
  c.innerHTML = skeleton(40) + skeleton(200) + skeleton(60);
  try {
    const inc = await api(`/v1/incidents/${id}`);
    const cert = inc.certificate && Object.keys(inc.certificate).length > 0 ? inc.certificate : null;
    let certValid = null;
    if (cert) {
      try { const v = await api(`/v1/incidents/${id}/certificates/pom-cert-v1/verify`); certValid = v.signature_valid; } catch(e) {}
    }

    qs("#view-title").textContent = `Incident: ${id}`;
    c.innerHTML = `
      <button class="btn btn-sm btn-outline" style="margin-bottom:16px" onclick="navigate('incidents')">← Back to Incidents</button>
      ${demoBadge()}
      <div style="display:flex;gap:12px;align-items:center;margin:8px 0 16px">
        ${badge(inc.status)}
        <span style="font-size:13px;color:var(--muted)">ID: ${inc.incident_id}</span>
      </div>

      <section>
        <h3 class="section-title" style="margin-top:0">Workflow Timeline</h3>
        <div style="display:flex;gap:12px;flex-wrap:wrap">
          ${step("Captured", true)}
          ${step("Replayed", !!inc.replay_result)}
          ${step("Fix Verified", !!inc.mutation_result)}
          ${step("Certified", !!cert)}
        </div>
      </section>

      <section>
        <h3 class="section-title">Evidence</h3>
        <div class="kv"><span class="kv-label">Root Hash</span><span class="kv-value" style="font-family:monospace;font-size:11px">${(inc.snapshot_summary?.root_hash||'—').substring(0,20)}...</span></div>
        <div class="kv"><span class="kv-label">Elements</span><span class="kv-value">${inc.snapshot_summary?.element_count||'—'}</span></div>
        <div class="kv"><span class="kv-label">Schema</span><span class="kv-value">v${inc.snapshot_summary?.schema_version||'—'}</span></div>
      </section>

      ${inc.replay_result ? `
      <section>
        <h3 class="section-title">Replay</h3>
        <div class="kv"><span class="kv-label">Decision</span><span class="kv-value" style="font-family:monospace;font-weight:800">${inc.replay_result.decision||'—'}</span></div>
        <div class="kv"><span class="kv-label">Status</span><span class="kv-value">${inc.replay_result.replay_status||'—'}</span></div>
      </section>` : ''}

      ${inc.mutation_result ? `
      <section>
        <h3 class="section-title">Fix Verification</h3>
        <div class="kv"><span class="kv-label">Original</span><span class="kv-value">${inc.mutation_result.original_decision}</span></div>
        <div class="kv"><span class="kv-label">Mutated</span><span class="kv-value" style="color:${inc.mutation_result.mitigated?'var(--green)':'var(--red)'}">${inc.mutation_result.mutated_decision}</span></div>
        <div class="kv"><span class="kv-label">Mitigated</span><span class="kv-value">${inc.mutation_result.mitigated ? '✓ Yes' : '✗ No'}</span></div>
      </section>` : ''}

      ${cert ? `
      <section>
        <h3 class="section-title">Proof</h3>
        <div class="kv"><span class="kv-label">Certificate</span><span class="kv-value">${cert.certificate_id}</span></div>
        <div class="kv"><span class="kv-label">Algorithm</span><span class="kv-value" style="font-family:monospace;font-size:11px">${cert.signing_algorithm}</span></div>
        <div class="kv"><span class="kv-label">Signature Valid</span><span class="kv-value" style="color:${certValid ? 'var(--green)' : 'var(--red)'}">${certValid === true ? '✓ Yes' : certValid === false ? '✗ No' : 'Unknown'}</span></div>
        <div class="kv"><span class="kv-label">Limitations</span><span class="kv-value" style="font-size:11px">${cert.known_limitations||'—'}</span></div>
      </section>` : ''}

      ${inc.custody ? `
      <section>
        <h3 class="section-title">Custody Chain</h3>
        ${(inc.custody||[]).map(c => `
          <div style="padding:6px 0;border-bottom:1px solid rgba(31,42,61,.3);font-size:12px">
            <span style="font-weight:700;color:var(--text)">${c.action}</span>
            <span style="color:var(--dim)"> by ${c.actor} </span>
            <span style="color:var(--muted)">${c.detail}</span>
            <span style="color:var(--dim);float:right">${formatDate(c.timestamp)}</span>
          </div>`).join("")}
      </section>` : ''}

      <div class="action-row" style="margin-top:16px">
        ${!inc.replay_result ? `<button class="btn" onclick="replayIncident('${id}');openInvestigation('${id}')">Run Replay</button>` : ''}
        ${inc.replay_result && !inc.mutation_result ? `<button class="btn" onclick="verifyFix('${id}');openInvestigation('${id}')">Verify Fix</button>` : ''}
        ${inc.mutation_result && !cert ? `<button class="btn" onclick="issueProof('${id}');openInvestigation('${id}')">Issue Proof</button>` : ''}
      </div>`;
  } catch(e) {
    c.innerHTML = error("Incident not found.");
  }
}

function step(label, done) {
  return `<div style="padding:6px 14px;border-radius:var(--radius);border:1px solid ${done?'var(--green)':'var(--border)'};background:${done?'rgba(34,197,94,.08)':'transparent'};font-size:12px;font-weight:700;color:${done?'var(--green)':'var(--dim)'}">${done?'✓':''} ${label}</div>`;
}

// ── REPLAY & VERIFY ──
function renderReplay(c) {
  c.innerHTML = empty("Replay & Verification", "Select an incident from the Incidents page to begin the replay and verification workflow.", "Go to Incidents", "navigate('incidents')");
}

// ── PROOFS ──
async function renderProofs(c) {
  try {
    const incidents = await api("/v1/incidents");
    const certified = incidents.filter(i => i.certificate && Object.keys(i.certificate).length > 0);
    if (!certified.length) { c.innerHTML = empty("No Proofs", "Issue a proof from a mitigated incident."); return; }
    c.innerHTML = `
      <table>
        <thead><tr><th>Certificate</th><th>Incident</th><th>Algorithm</th><th>Actions</th></tr></thead>
        <tbody>${certified.map(inc => `
          <tr>
            <td>${demoBadge()} ${inc.certificate.certificate_id}</td>
            <td><span style="cursor:pointer;text-decoration:underline" onclick="openInvestigation('${inc.incident_id}')">${inc.incident_id}</span></td>
            <td style="font-family:monospace;font-size:10px">${inc.certificate.signing_algorithm}</td>
            <td class="action-row">
              <button class="btn btn-sm btn-outline" onclick="verifyCert('${inc.incident_id}')">Verify</button>
              <a href="/v1/incidents/${inc.incident_id}/certificates/pom-cert-v1/download" class="btn btn-sm btn-outline" style="text-decoration:none">Download</a>
            </td>
          </tr>`).join("")}</tbody>
      </table>`;
  } catch(e) { c.innerHTML = error("Could not load proofs."); }
}

async function verifyCert(id) {
  try { const v = await api(`/v1/incidents/${id}/certificates/pom-cert-v1/verify`); alert(v.signature_valid ? "Signature valid ✓" : "Signature invalid ✗"); } catch(e) { alert("Verification failed"); }
}

// ── SCAFFOLDS ──
function renderScenarios(c) { c.innerHTML = empty("Scenarios", "Scenario testing is planned and not yet available.", null, null) + '<div style="text-align:center;margin-top:16px">'+planBadge()+'</div>'; }
function renderGovernance(c) {
  c.innerHTML = ['Labels','Claim Scope','Regulatory Mappings','Retention','Audit Events'].map(s =>
    `<div class="stat" style="margin-bottom:12px"><div style="display:flex;align-items:center;gap:8px"><span style="font-size:14px;font-weight:700">${s}</span>${planBadge()}</div><div style="font-size:12px;color:var(--muted);margin-top:4px">Planned — not yet available.</div></div>`
  ).join("");
}
function renderSettings(c) {
  c.innerHTML = `
    <div class="stat" style="margin-bottom:12px"><div style="font-size:14px;font-weight:700">Organization</div><div style="font-size:12px;color:var(--muted);margin-top:4px">Acme Assurance Demo</div><div style="font-size:11px;color:var(--dim);margin-top:4px">ID: org:acme-demo</div></div>
    ${['Users & Roles','API Keys','Integrations','Entitlements'].map(s => `<div class="stat" style="margin-bottom:12px"><div style="display:flex;align-items:center;gap:8px"><span style="font-size:14px;font-weight:700">${s}</span>${planBadge()}</div></div>`).join("")}
  `;
}

// ── Start ──
render();
</script>
</body>
</html>
```

---

# BATCH 3: Verify everything works

After replacing `static/app/index.html`, run:

```bash
# Backend tests
cd /Users/hardyk/notary-platform
.venv/bin/pytest -q         # should pass (77+)
.venv/bin/ruff check .       # should be clean
.venv/bin/mypy src           # should be clean

# Start locally
.venv/bin/uvicorn notary_platform.api_server.main:app --host 0.0.0.0 --port 8001

# Seed demo data
curl -X POST http://localhost:8001/v1/platform/seed-demo

# Open app
open http://localhost:8001/app
```

**Verify checklist:**
- [ ] Home shows setup health stats, active queues, recent proofs, next action
- [ ] Switch env to staging → empty states, no data
- [ ] Switch back to demo → data returns
- [ ] DEMO badge visible on demo env
- [ ] Incidents page shows 5 incidents (after seeding)
- [ ] Replay button on ingested incident works
- [ ] Verify Fix button on replayed incident works
- [ ] Issue Proof button on mitigated incident works
- [ ] Click investigate → full Investigation view with timeline, evidence, replay, fix, proof, custody
- [ ] Proofs page shows certified incidents with verify/download buttons
- [ ] Agents page shows 4 agents with status dots
- [ ] Onboarding checklist renders all 6 steps
- [ ] Scenarios, Governance, Settings show planned scaffolds
- [ ] Kill API → error state on all pages
- [ ] No console errors

---

# BATCH 4: Build, deploy, verify on AWS

```bash
# Commit
cd /Users/hardyk/notary-platform
git add -A && git commit -m "Notary Platform: full SPA + seed demo + extended Home API" && git push origin main

# Build image
TAG="build-$(date +%Y%m%d-%H%M%S)-amd64"
REPO="447633181871.dkr.ecr.us-east-2.amazonaws.com/notary-api"
docker buildx build --platform linux/amd64 --build-arg INSTALL_CLOUD=1 -t "$REPO:$TAG" --push .

# Deploy
# (use existing taskdef.json template, register new revision, update service, wait for rollout)
```

---

# What's NOT in this build pass (deferred to later batches)

These features are in the product plan but deferred:
- Systems: Add/Test Connection, detail drawer actions (table + read-only is in this build)
- Capture: Create/Edit policy UI (table + read-only is in this build)
- Replay & Verification: Dedicated workflow screen (uses Investigation + inline actions for now)
- Agent detail drawer: Full profile with linked incidents (basic drawer is in this build)
- Environment-based filtering on Agents/Systems/Capture tables
- Pagination on Incidents
