"""Forensic Control Center — visual incident investigation UI for the prototype."""

from __future__ import annotations

from html import escape
from typing import Any, Callable

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from notary_platform.api_server.routers.incidents import set_demo_agent, storage
from notary_platform.demo_scenarios import SCENARIOS, build_snapshot, get_scenario
from notary_platform.models import Incident
from notary_platform.replay_engine.cassette import ResponseCassette

router = APIRouter(tags=["dashboard"])


def _safe(value: Any) -> str:
    return escape(str(value))


def _scenario_agent_factory(scenario_id: str) -> Callable[..., str]:
    scenario = get_scenario(scenario_id)

    def agent(cassette: ResponseCassette, **kwargs: Any) -> str:
        mode = kwargs.get("mode", "default")
        if scenario.scenario_id == "lending-denial":
            threshold = int(kwargs.get("threshold", 700))
            result = cassette.lookup("POST", "https://demo.notary.local/credit-api")
            score = scenario.cassette_response.get("score", 0)
            if result is not None and isinstance(result.get("response"), dict):
                score = result["response"].get("score", score)
            return "APPROVE" if int(score) >= threshold else "DENY"

        if scenario.scenario_id == "prior-auth-denial":
            if kwargs.get("require_human_review_for_high_risk_note") or mode == "fixed":
                return "ESCALATE_TO_HUMAN_REVIEW"
            return "DENY"

        if scenario.scenario_id == "hiring-screen-rejection":
            if kwargs.get("remove_age_proxy") or mode == "fixed":
                return "ADVANCE_TO_REVIEW"
            return "REJECT"

        return scenario.original_decision

    return agent


def _status_class(status: str) -> str:
    return {
        "ingested": "pending",
        "replayed": "info",
        "mitigated": "success",
        "certified": "certified",
    }.get(status, "pending")


def _workflow_steps(status: str) -> str:
    order = ["ingested", "replayed", "mitigated", "certified"]
    current_index = order.index(status) if status in order else 0
    labels = {
        "ingested": "Evidence sealed",
        "replayed": "Failure reproduced",
        "mitigated": "Fix verified",
        "certified": "Proof issued",
    }

    return "".join(
        f"""
        <div class="step {'done' if idx <= current_index else 'todo'}">
          <div class="dot"></div>
          <div>
            <div class="step-name">{step.title()}</div>
            <div class="step-sub">{labels[step]}</div>
          </div>
        </div>
        """
        for idx, step in enumerate(order)
    )


def _mode_copy(mode: str) -> tuple[str, str]:
    if mode == "sandbox":
        return (
            "Sandbox escalation view",
            "Sandbox mode shows where a real provider/customer test system would be used if a"
            " fix introduced new external calls. In this prototype, sandbox adapters are"
            " intentionally not configured.",
        )
    if mode == "production":
        return (
            "Production capture view",
            "Production mode shows where the original decision was captured. Notary never replays or tests fixes against production systems.",
        )
    return (
        "Cassette replay view",
        "Cassette mode is the active prototype path: replay runs from sealed recorded responses, independent of the provider's current state.",
    )


def _scenario_selector(active: str) -> str:
    cards = ""
    for scenario in SCENARIOS.values():
        selected = "selected" if scenario.scenario_id == active else ""
        cards += f"""
        <a class="scenario {selected}" href="/dashboard?scenario_id={scenario.scenario_id}">
          <div class="scenario-title">{_safe(scenario.title)}</div>
          <div class="scenario-meta">{_safe(scenario.industry)}</div>
          <div class="scenario-risk">{_safe(scenario.risk)}</div>
        </a>
        """
    return f"<div class='scenario-grid'>{cards}</div>"


def _find_active_incident(scenario_id: str) -> Incident | None:
    for incident in reversed(storage.list_incidents()):
        snapshot = storage.get_snapshot(incident.incident_id)
        if snapshot and snapshot.get("scenario_id") == scenario_id:
            return incident
    return None


def _action_buttons(incident_id: str, status: str, scenario_id: str) -> str:
    if status == "ingested":
        return f"""
        <button class="primary" onclick="replay('{incident_id}')">Replay failure</button>
        <p class="hint">Replay proves whether the same bad decision can be reproduced from sealed evidence.</p>
        """
    if status == "replayed":
        return f"""
        <button class="primary" onclick="applyFix('{incident_id}', '{scenario_id}')">Apply scenario fix</button>
        <p class="hint">Runs the scenario-specific fix against the same recorded conditions.</p>
        """
    if status == "mitigated":
        return f"""
        <button class="primary" onclick="issueCert('{incident_id}')">Issue certificate</button>
        <p class="hint">Creates signed proof that the fix resolved this incident.</p>
        """
    if status == "certified":
        return f"""
        <button class="primary" onclick="verifySignature('{incident_id}')">Verify signature</button>
        <a class="secondary link-button" href="/v1/certificates/{incident_id}">Technical JSON</a>
        <div id="verify-panel" class="verify-panel"></div>
        """
    return ""


def _node_graph(scenario_id: str, mode: str) -> str:
    scenario = get_scenario(scenario_id)
    mode_title, mode_body = _mode_copy(mode)

    node_width = 170
    gap = 38
    start_x = 20
    y = 130

    nodes = ""
    edges = ""
    for idx, node in enumerate(scenario.nodes):
        x = start_x + idx * (node_width + gap)
        cls = "failure" if node.failure else ("evidence" if node.kind == "tool" else "normal")
        nodes += f"""
        <g class="node {cls}">
          <rect x="{x}" y="{y}" width="{node_width}" height="110" rx="18"></rect>
          <text x="{x + node_width / 2}" y="{y + 34}" text-anchor="middle">{_safe(node.label)}</text>
          <text x="{x + node_width / 2}" y="{y + 65}" text-anchor="middle" class="small">{_safe(node.kind)}</text>
          <text x="{x + node_width / 2}" y="{y + 92}" text-anchor="middle" class="small">{'failure node' if node.failure else 'sealed step'}</text>
        </g>
        """
        if idx < len(scenario.nodes) - 1:
            x1 = x + node_width
            x2 = x + node_width + gap
            edge_cls = "edge danger" if scenario.nodes[idx + 1].failure else "edge"
            edges += f'<line x1="{x1}" y1="{y + 55}" x2="{x2}" y2="{y + 55}" class="{edge_cls}" />'

    return f"""
    <div class="graph-copy">
      <div class="mode-title">{_safe(mode_title)}</div>
      <p>{_safe(mode_body)}</p>
    </div>
    <svg viewBox="0 0 1060 360" class="graph">
      <defs>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
          <path d="M0,0 L0,6 L9,3 z" fill="#38bdf8"></path>
        </marker>
      </defs>
      {edges}
      {nodes}
    </svg>
    """


def _proof_panel(inc: Incident | None, scenario_id: str, mode: str) -> str:
    scenario = get_scenario(scenario_id)

    if inc is None:
        status = "not seeded"
        replay_decision = "not run"
        mutated_decision = "not run"
        certificate_state = "not issued"
        signature_state = "pending"
    else:
        data = inc.to_dict()
        status = data["status"]
        replay_decision = data.get("replay_result", {}).get("decision", "not run")
        mutated_decision = data.get("mutation_result", {}).get("mutated_decision", "not run")
        certificate = data.get("certificate") or {}
        certificate_state = "issued" if certificate else "not issued"
        signature_state = "available" if certificate else "pending"

    return f"""
    <section class="proof-grid">
      <div class="proof-card">
        <h3>Recorded Conditions</h3>
        <div class="detail-row"><span>Model</span><strong>{_safe(scenario.model_version)}</strong></div>
        <div class="detail-row"><span>Policy</span><strong>{_safe(scenario.policy_version)}</strong></div>
        <div class="detail-row"><span>Temperature</span><strong>{scenario.temperature}</strong></div>
        <div class="detail-row"><span>Seed</span><strong>{scenario.seed}</strong></div>
        <div class="detail-row"><span>External system</span><strong>{_safe(scenario.external_system)}</strong></div>
        <div class="detail-row"><span>Cassette response</span><code>{_safe(scenario.cassette_response)}</code></div>
      </div>

      <div class="proof-card">
        <h3>Replay Proof</h3>
        <p class="label">What replay proves</p>
        <p>The original decision can be reproduced from sealed evidence, without calling production.</p>
        <div class="compare">
          <div><span>Original</span><strong>{_safe(scenario.original_decision)}</strong></div>
          <div><span>Replay</span><strong>{_safe(replay_decision)}</strong></div>
        </div>
        <p class="result">{'Reproduced' if status in ('replayed', 'mitigated', 'certified') else 'Not run yet'}</p>
      </div>

      <div class="proof-card">
        <h3>Fix Verification</h3>
        <p class="label">What fix testing proves</p>
        <p>The customer-supplied fix is tested against the same recorded conditions.</p>
        <div class="compare">
          <div><span>Expected</span><strong>{_safe(scenario.expected_correct_behavior)}</strong></div>
          <div><span>Fixed output</span><strong>{_safe(mutated_decision)}</strong></div>
        </div>
        <p class="result">{'Fix verified' if status in ('mitigated', 'certified') else 'Not verified yet'}</p>
      </div>

      <div class="proof-card">
        <h3>Certificate</h3>
        <p class="label">Who verifies it</p>
        <p>Compliance, legal, or auditors can verify the signed proof without trusting raw logs.</p>
        <div class="compare">
          <div><span>Certificate</span><strong>{certificate_state}</strong></div>
          <div><span>Signature</span><strong>{signature_state}</strong></div>
        </div>
      </div>
    </section>
    """


def _case_cards() -> str:
    cards = ""
    for incident in storage.list_incidents():
        data = incident.to_dict()
        snapshot = storage.get_snapshot(incident.incident_id) or {}
        scenario_id = snapshot.get("scenario_id", "lending-denial")
        scenario = get_scenario(str(scenario_id))
        cards += f"""
        <a class="case-card" href="/dashboard?scenario_id={scenario.scenario_id}">
          <div class="case-id">{incident.incident_id}</div>
          <div class="badge {_status_class(data['status'])}">{data['status']}</div>
          <div class="case-meta">{_safe(scenario.title)}</div>
          <div class="hash">{_safe(data['snapshot_summary'].get('root_hash', ''))[:22]}...</div>
        </a>
        """
    return cards


def _page(content: str) -> str:
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>Notary Forensic Control Center</title>
<style>
:root {{
  --bg: #050812;
  --panel: rgba(13, 19, 32, .92);
  --panel2: #111827;
  --line: #1f2a3d;
  --text: #e5eefc;
  --muted: #91a4c0;
  --blue: #38bdf8;
  --green: #22c55e;
  --amber: #f59e0b;
  --red: #ef4444;
  --purple: #a78bfa;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(56,189,248,.16), transparent 32rem),
    radial-gradient(circle at top right, rgba(167,139,250,.14), transparent 30rem),
    var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
a {{ color: var(--blue); text-decoration: none; }}
.shell {{ max-width: 1360px; margin: 0 auto; padding: 28px; }}
.topbar {{ display:flex; justify-content:space-between; gap:18px; align-items:center; margin-bottom:24px; }}
.brand {{ font-weight: 900; color: var(--blue); letter-spacing:.12em; text-transform:uppercase; }}
button, .link-button {{
  border: 0; border-radius: 12px; padding: 10px 14px; font-weight: 800; cursor: pointer;
}}
.primary {{ background: linear-gradient(135deg, #06b6d4, #3b82f6); color: white; }}
.secondary {{ background:#111827; color:var(--text); border:1px solid var(--line); }}
.hero {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-start; margin-bottom:20px; }}
.eyebrow {{ color: var(--blue); text-transform:uppercase; font-size:12px; letter-spacing:.16em; font-weight:900; }}
h1 {{ font-size:44px; margin:4px 0 8px; }}
.subtitle {{ color:var(--muted); max-width:760px; margin:0; }}
.scenario-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:20px; }}
.scenario {{ display:block; padding:16px; border:1px solid var(--line); border-radius:18px; background:var(--panel); color:var(--text); }}
.scenario.selected {{ border-color:var(--blue); box-shadow:0 0 0 2px rgba(56,189,248,.18); }}
.scenario-title {{ font-weight:900; margin-bottom:6px; }}
.scenario-meta, .scenario-risk {{ color:var(--muted); font-size:13px; }}
.mode-toggle {{ display:flex; gap:8px; margin:14px 0 20px; }}
.mode-toggle a {{ padding:9px 12px; border:1px solid var(--line); border-radius:999px; color:var(--muted); }}
.mode-toggle a.active {{ color:var(--text); border-color:var(--blue); background:rgba(56,189,248,.12); }}
.workspace {{ display:grid; grid-template-columns:1fr 360px; gap:18px; margin-bottom:18px; }}
.panel, .evidence-panel, .proof-card, .timeline, .actions, .case-card {{
  background:var(--panel); border:1px solid var(--line); border-radius:18px; box-shadow:0 24px 80px rgba(0,0,0,.32);
}}
.panel {{ padding:18px; }}
.evidence-panel, .proof-card, .actions {{ padding:18px; }}
.panel-title {{ color:var(--muted); text-transform:uppercase; font-size:12px; font-weight:900; letter-spacing:.14em; margin-bottom:14px; }}
.graph {{ width:100%; min-height:330px; }}
.edge {{ stroke: var(--blue); stroke-width:4; marker-end:url(#arrow); opacity:.72; animation:pulse 2.4s infinite; }}
.edge.danger {{ stroke:var(--red); }}
@keyframes pulse {{ 0% {{ opacity:.25 }} 50% {{ opacity:1 }} 100% {{ opacity:.25 }} }}
.node rect {{ fill:#101827; stroke:#2e405f; stroke-width:2; filter:drop-shadow(0 0 18px rgba(56,189,248,.08)); }}
.node.evidence rect {{ stroke:var(--blue); }}
.node.failure rect {{ stroke:var(--red); fill:#1a1117; filter:drop-shadow(0 0 22px rgba(239,68,68,.25)); }}
.node text {{ fill:var(--text); font-size:15px; font-weight:900; }}
.node .small {{ fill:var(--muted); font-size:12px; font-weight:700; }}
.graph-copy {{ color:var(--muted); border-bottom:1px solid var(--line); padding-bottom:12px; margin-bottom:8px; }}
.mode-title {{ color:var(--text); font-weight:900; }}
.detail-row {{ display:flex; justify-content:space-between; gap:12px; border-bottom:1px solid var(--line); padding:10px 0; }}
.detail-row span {{ color:var(--muted); }}
code {{ color:#93c5fd; font-size:12px; }}
.badge {{ display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:900; text-transform:uppercase; }}
.pending {{ color:#fbbf24; background:rgba(245,158,11,.14); }}
.info {{ color:var(--blue); background:rgba(56,189,248,.14); }}
.success {{ color:var(--green); background:rgba(34,197,94,.14); }}
.certified {{ color:var(--purple); background:rgba(167,139,250,.16); }}
.timeline {{ display:grid; grid-template-columns:repeat(4,1fr); margin-bottom:18px; overflow:hidden; }}
.step {{ display:flex; gap:12px; padding:16px; align-items:center; border-right:1px solid var(--line); }}
.step:last-child {{ border-right:0; }}
.dot {{ width:14px; height:14px; border-radius:50%; background:#334155; }}
.step.done .dot {{ background:var(--green); box-shadow:0 0 0 4px rgba(34,197,94,.16); }}
.step-name {{ font-weight:900; }}
.step-sub {{ color:var(--muted); font-size:12px; }}
.proof-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:18px; }}
.proof-card h3 {{ margin:0 0 8px; }}
.label {{ color:var(--blue); text-transform:uppercase; font-size:11px; font-weight:900; }}
.compare {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:12px 0; }}
.compare div {{ background:#0b1120; border:1px solid var(--line); border-radius:12px; padding:10px; }}
.compare span {{ display:block; color:var(--muted); font-size:12px; }}
.result, .hint {{ color:var(--muted); }}
.verify-panel {{ margin-top:14px; padding:12px; border:1px solid var(--line); border-radius:12px; background:#0b1120; }}
.case-list {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; margin-top:14px; }}
.case-card {{ display:block; padding:14px; color:var(--text); }}
.hash, .case-meta {{ color:var(--muted); font-size:13px; margin-top:8px; }}
@media(max-width: 980px) {{ .scenario-grid,.workspace,.proof-grid,.timeline {{ grid-template-columns:1fr; }} }}
</style>
<script>
function replay(id) {{ fetch('/v1/incidents/' + id + '/replay', {{method:'POST'}}).then(() => location.reload()); }}
function applyFix(id, scenario) {{
  let fixes = {{
    'lending-denial': {{fix_config:{{threshold:620}}, expected_correct_behavior:'APPROVE'}},
    'prior-auth-denial': {{fix_config:{{require_human_review_for_high_risk_note:true}}, expected_correct_behavior:'ESCALATE_TO_HUMAN_REVIEW'}},
    'hiring-screen-rejection': {{fix_config:{{remove_age_proxy:true, route_borderline_to_human_review:true}}, expected_correct_behavior:'ADVANCE_TO_REVIEW'}}
  }};
  fetch('/v1/incidents/' + id + '/mutation', {{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify(fixes[scenario])
  }}).then(() => location.reload());
}}
function issueCert(id) {{ fetch('/v1/certificates/' + id, {{method:'POST'}}).then(() => location.reload()); }}
function verifySignature(id) {{
  let panel = document.getElementById('verify-panel');
  panel.innerHTML = '<div>1. Certificate loaded ✓</div><div>2. Digest recomputed ✓</div><div>3. Checking signature…</div>';
  fetch('/v1/certificates/' + id + '/verify')
    .then(r => r.json())
    .then(j => {{
      panel.innerHTML = '<div>1. Certificate loaded ✓</div>'
        + '<div>2. Digest recomputed ✓</div>'
        + '<div>3. Signature check ' + (j.signature_valid ? '✓' : '✕') + '</div>'
        + '<strong>Result: ' + (j.signature_valid ? 'valid and unaltered' : 'invalid') + '</strong>'
        + '<details><summary>Technical JSON</summary><pre>'
        + JSON.stringify(j, null, 2) + '</pre></details>';
    }});
}}
</script>
</head>
<body><div class="shell">{content}</div></body></html>"""


def _render_dashboard(scenario_id: str, mode: str) -> str:
    scenario = get_scenario(scenario_id)
    incident = _find_active_incident(scenario_id)

    badges = ""
    if incident:
        data = incident.to_dict()
        badges = f"<span class='badge {_status_class(data['status'])}'>{data['status']}</span>"
    else:
        badges = "<span class='badge pending'>not seeded</span>"

    content = f"""
    <nav class="topbar">
      <div class="brand">NOTARY · FORENSIC CONTROL CENTER</div>
      <form method="post" action="/v1/demo/lending-seed?scenario_id={scenario_id}">
        <button class="secondary" type="submit">Seed selected scenario</button>
      </form>
    </nav>

    <section class="hero">
      <div>
        <div class="eyebrow">{_safe(scenario.industry)}</div>
        <h1>{_safe(scenario.title)}</h1>
        <p class="subtitle">{_safe(scenario.risk)}</p>
      </div>
      <div>{badges}</div>
    </section>

    {_scenario_selector(scenario_id)}

    <div class="mode-toggle">
      <a class="{ 'active' if mode == 'cassette' else '' }" href="/dashboard?scenario_id={scenario_id}&mode=cassette">Cassette</a>
      <a class="{ 'active' if mode == 'sandbox' else '' }" href="/dashboard?scenario_id={scenario_id}&mode=sandbox">Sandbox</a>
      <a class="{ 'active' if mode == 'production' else '' }" href="/dashboard?scenario_id={scenario_id}&mode=production">Production</a>
    </div>

    <section class="workspace">
      <div class="panel">
        <div class="panel-title">Decision graph</div>
        {_node_graph(scenario_id, mode)}
      </div>
      <aside class="evidence-panel">
        <div class="panel-title">Recorded system conditions</div>
        <div class="detail-row"><span>Model</span><strong>{_safe(scenario.model_name)}</strong></div>
        <div class="detail-row"><span>Model version</span><strong>{_safe(scenario.model_version)}</strong></div>
        <div class="detail-row"><span>Policy version</span><strong>{_safe(scenario.policy_version)}</strong></div>
        <div class="detail-row"><span>Temperature</span><strong>{scenario.temperature}</strong></div>
        <div class="detail-row"><span>Seed</span><strong>{scenario.seed}</strong></div>
        <div class="detail-row"><span>Timestamp</span><strong>{_safe(scenario.timestamp)}</strong></div>
        <div class="detail-row"><span>External system</span><strong>{_safe(scenario.external_system)}</strong></div>
        <div class="detail-row"><span>Cassette response</span><code>{_safe(scenario.cassette_response)}</code></div>
      </aside>
    </section>

    <section class="timeline">
      {_workflow_steps(incident.to_dict()['status'] if incident else 'ingested')}
    </section>

    {_proof_panel(incident, scenario_id, mode)}

    <section class="actions">
      { _action_buttons(incident.incident_id, incident.to_dict()['status'], scenario_id) if incident
        else '<form method="post" action="/v1/demo/lending-seed?scenario_id=' + scenario_id + '">'
        + '<button class="primary" type="submit">Seed this scenario</button></form>'
        + '<p class="hint">Create a sealed demo incident to begin the proof workflow.</p>' }
    </section>

    <section>
      <div class="panel-title">Case files</div>
      <div class="case-list">{_case_cards()}</div>
    </section>
    """
    return _page(content)


@router.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(_render_dashboard("lending-denial", "cassette"))


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    scenario_id: str = Query("lending-denial"),
    mode: str = Query("cassette"),
) -> HTMLResponse:
    if mode not in {"cassette", "sandbox", "production"}:
        mode = "cassette"
    return HTMLResponse(_render_dashboard(scenario_id, mode))


@router.post("/v1/demo/lending-seed", response_class=HTMLResponse)
def seed_lending_demo(scenario_id: str = Query("lending-denial")) -> RedirectResponse:
    scenario = get_scenario(scenario_id)
    set_demo_agent(_scenario_agent_factory(scenario.scenario_id))
    storage.create_incident(build_snapshot(scenario))
    return RedirectResponse(url=f"/dashboard?scenario_id={scenario.scenario_id}", status_code=303)
