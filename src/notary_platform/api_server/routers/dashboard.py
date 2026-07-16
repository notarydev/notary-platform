"""Forensic Control Center — visual incident investigation UI for the prototype."""

from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from notary_platform.api_server.routers.incidents import set_demo_agent, storage
from notary_platform.replay_engine.cassette import ResponseCassette
from notary_platform.snapshot import CapturedElement, _compute_root_hash, _seal_element

router = APIRouter(tags=["dashboard"])

_DEMO_SECRET = b"demo-secret-key-32-bytes-long!!!"
_DEMO_SCORE = 650
_ORIGINAL_THRESHOLD = 700
_FIXED_THRESHOLD = 620


def _lending_agent(cassette: ResponseCassette, threshold: int = _ORIGINAL_THRESHOLD) -> str:
    """Demo lending agent that reads credit score from the sealed cassette."""
    result = cassette.lookup("POST", "https://api.example.com/credit-check")
    if result is None:
        return "UNKNOWN"
    score = result.get("response", {}).get("score", 0)
    return "APPROVE" if score >= threshold else "DENY"


def _make_demo_snapshot() -> dict[str, Any]:
    """Create a sealed lending-denial snapshot for the prototype demo."""
    elements: list[dict[str, Any]] = [
        {
            "kind": "llm",
            "payload": {
                "prompt": "Evaluate lending application for applicant A-1027.",
                "response": "Use credit score and policy threshold to decide.",
                "metadata": {"model": "demo-model", "purpose": "policy_context"},
            },
        },
        {
            "kind": "http",
            "payload": {
                "request": {
                    "method": "POST",
                    "url": "https://api.example.com/credit-check",
                    "body": '{"applicant_id":"A-1027"}',
                },
                "response": {"score": _DEMO_SCORE},
                "status": 200,
            },
        },
        {
            "kind": "decision",
            "payload": {
                "decision": "DENY",
                "reason": f"score {_DEMO_SCORE} below threshold {_ORIGINAL_THRESHOLD}",
                "threshold": _ORIGINAL_THRESHOLD,
            },
        },
    ]

    prev_hash = b"\x00" * 32
    elem_hashes: list[bytes] = []
    sealed: list[dict[str, Any]] = []

    for e in elements:
        ce = CapturedElement(kind=e["kind"], payload=e.get("payload", {}))
        h = _seal_element(prev_hash, ce.canonical_bytes(), _DEMO_SECRET)
        elem_hashes.append(h)
        sealed.append({"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()})
        prev_hash = h

    root = _compute_root_hash(elem_hashes)
    return {
        "schema_version": 1,
        "timestamp": "2025-07-15T00:00:00Z",
        "elements": sealed,
        "merkle_chain": [h.hex() for h in elem_hashes],
        "root_hash": root,
    }


def _safe(value: Any) -> str:
    return escape(str(value))


def _status_class(status: str) -> str:
    return {
        "ingested": "pending",
        "replayed": "info",
        "mitigated": "success",
        "certified": "certified",
    }.get(status, "pending")


def _find_http_score(snapshot: dict[str, Any]) -> Any:
    for elem in snapshot.get("elements", []):
        if elem.get("kind") == "http":
            response = elem.get("payload", {}).get("response", {})
            if isinstance(response, dict) and "score" in response:
                return response["score"]
    return "unknown"


def _find_original_decision(snapshot: dict[str, Any]) -> str:
    for elem in snapshot.get("elements", []):
        if elem.get("kind") == "decision":
            payload = elem.get("payload", {})
            return str(payload.get("decision", "unknown"))
    return "unknown"


def _workflow_steps(status: str) -> str:
    order = ["ingested", "replayed", "mitigated", "certified"]
    current_index = order.index(status) if status in order else 0

    labels = {
        "ingested": "Evidence sealed",
        "replayed": "Failure reproduced",
        "mitigated": "Fix verified",
        "certified": "Proof issued",
    }

    html = ""
    for idx, step in enumerate(order):
        cls = "done" if idx <= current_index else "todo"
        html += f"""
        <div class="step {cls}">
          <div class="dot"></div>
          <div>
            <div class="step-name">{step.title()}</div>
            <div class="step-sub">{labels[step]}</div>
          </div>
        </div>
        """
    return html


def _action_buttons(incident_id: str, status: str) -> str:
    if status == "ingested":
        return f"""
        <button class="primary" onclick="replay('{incident_id}')">Replay failure</button>
        <p class="hint">Replay proves whether the same bad decision can be reproduced from sealed evidence.</p>
        """
    if status == "replayed":
        return f"""
        <button class="primary" onclick="applyFix('{incident_id}')">Apply fix: threshold 620</button>
        <p class="hint">Runs the fixed decision rule against the same recorded score.</p>
        """
    if status == "mitigated":
        return f"""
        <button class="primary" onclick="issueCert('{incident_id}')">Issue certificate</button>
        <p class="hint">Creates signed proof that the fix resolved this incident.</p>
        """
    if status == "certified":
        return f"""
        <a class="primary link-button" href="/v1/certificates/{incident_id}">View certificate JSON</a>
        <a class="secondary link-button" href="/v1/certificates/{incident_id}/verify">Verify signature</a>
        """
    return ""


def _incident_card(inc: object) -> str:
    inc_d = inc.to_dict()  # type: ignore[attr-defined]
    incident_id = inc_d["incident_id"]
    status = inc_d["status"]
    root = inc_d["snapshot_summary"].get("root_hash", "")
    element_count = inc_d["snapshot_summary"].get("element_count", "?")

    return f"""
    <a class="case-card" href="/dashboard?incident_id={incident_id}">
      <div class="case-id">{incident_id}</div>
      <div class="badge {_status_class(status)}">{status}</div>
      <div class="case-meta">{element_count} sealed elements</div>
      <div class="hash">{root[:20]}...</div>
    </a>
    """


def _selected_incident() -> object | None:
    incidents = storage.list_incidents()
    return incidents[-1] if incidents else None


def _control_center(inc: object | None) -> str:
    if inc is None:
        return """
        <section class="empty">
          <h2>No incident loaded</h2>
          <p>Seed the lending demo to create a sealed incident and walk through replay, fix verification, and certificate issuance.</p>
          <form method="post" action="/v1/demo/lending-seed">
            <button class="primary" type="submit">Seed Lending Demo</button>
          </form>
        </section>
        """

    inc_d = inc.to_dict()  # type: ignore[attr-defined]
    incident_id = inc_d["incident_id"]
    status = inc_d["status"]
    snapshot = storage.get_snapshot(incident_id) or {}

    score = _find_http_score(snapshot)
    original_decision = _find_original_decision(snapshot)
    replay_result = inc_d.get("replay_result") or {}
    mutation_result = inc_d.get("mutation_result") or {}
    certificate = inc_d.get("certificate") or {}

    replay_decision = replay_result.get("decision", "not run")
    mutated_decision = mutation_result.get("mutated_decision", "not run")
    fix_config = mutation_result.get("fix_config", {"threshold": _FIXED_THRESHOLD})
    cert_status = "issued" if certificate else "not issued"
    signature_state = "available" if certificate else "pending"

    return f"""
    <section class="case-header">
      <div>
        <div class="eyebrow">Forensic Control Center</div>
        <h1>Incident {incident_id}</h1>
        <p class="subtitle">A sealed AI lending decision, replayed from cassette evidence and verified through a fix.</p>
      </div>
      <div class="header-badges">
        <span class="badge {_status_class(status)}">{status}</span>
        <span class="badge sealed">root sealed</span>
        <span class="badge method">cassette replay</span>
      </div>
    </section>

    <section class="workspace">
      <div class="graph-panel">
        <div class="panel-title">Decision Path</div>
        <svg viewBox="0 0 980 390" class="graph">
          <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#38bdf8"></path>
            </marker>
          </defs>

          <line x1="120" y1="195" x2="270" y2="195" class="edge" />
          <line x1="390" y1="195" x2="540" y2="195" class="edge" />
          <line x1="660" y1="195" x2="810" y2="195" class="edge danger" />

          <g class="node">
            <rect x="25" y="145" width="170" height="100" rx="18" />
            <text x="110" y="178" text-anchor="middle">Application</text>
            <text x="110" y="207" text-anchor="middle" class="small">Applicant A-1027</text>
          </g>

          <g class="node">
            <rect x="260" y="145" width="170" height="100" rx="18" />
            <text x="345" y="178" text-anchor="middle">Policy Context</text>
            <text x="345" y="207" text-anchor="middle" class="small">LLM / rules</text>
          </g>

          <g class="node evidence">
            <rect x="495" y="145" width="190" height="100" rx="18" />
            <text x="590" y="178" text-anchor="middle">Credit API</text>
            <text x="590" y="207" text-anchor="middle" class="small">score = {_safe(score)}</text>
          </g>

          <g class="node failure">
            <rect x="760" y="118" width="190" height="154" rx="22" />
            <text x="855" y="158" text-anchor="middle">Decision Rule</text>
            <text x="855" y="190" text-anchor="middle" class="small">threshold = {_ORIGINAL_THRESHOLD}</text>
            <text x="855" y="226" text-anchor="middle" class="decision">DENY</text>
            <text x="855" y="254" text-anchor="middle" class="small danger-text">failure point</text>
          </g>
        </svg>

        <div class="meaning">
          <strong>What this graph shows:</strong> Notary is not listing logs. It is reconstructing the decision path and highlighting the node where the outcome became wrong.
        </div>
      </div>

      <aside class="evidence-panel">
        <div class="panel-title">Evidence Detail</div>
        <div class="detail-row"><span>Recorded score</span><strong>{_safe(score)}</strong></div>
        <div class="detail-row"><span>Original threshold</span><strong>{_ORIGINAL_THRESHOLD}</strong></div>
        <div class="detail-row"><span>Original decision</span><strong>{_safe(original_decision)}</strong></div>
        <div class="detail-row"><span>Root hash</span><code>{_safe(inc_d["snapshot_summary"].get("root_hash", ""))[:32]}...</code></div>
        <div class="detail-row"><span>Evidence source</span><strong>sealed cassette</strong></div>
      </aside>
    </section>

    <section class="timeline">
      {_workflow_steps(status)}
    </section>

    <section class="proof-grid">
      <div class="proof-card">
        <h3>Replay Proof</h3>
        <p class="label">Question</p>
        <p>Can the original bad decision be reproduced from the sealed record?</p>
        <div class="compare">
          <div><span>Original</span><strong>{_safe(original_decision)}</strong></div>
          <div><span>Replay</span><strong>{_safe(replay_decision)}</strong></div>
        </div>
        <p class="result">{'Failure reproduced from sealed cassette.' if status in ('replayed', 'mitigated', 'certified') else 'Replay has not run yet.'}</p>
      </div>

      <div class="proof-card">
        <h3>Fix Verification</h3>
        <p class="label">Question</p>
        <p>Does the customer’s fix resolve the incident under the same conditions?</p>
        <div class="compare">
          <div><span>Fix</span><strong>{_safe(fix_config)}</strong></div>
          <div><span>Fixed output</span><strong>{_safe(mutated_decision)}</strong></div>
        </div>
        <p class="result">{'Fix verified against original conditions.' if status in ('mitigated', 'certified') else 'Fix verification has not run yet.'}</p>
      </div>

      <div class="proof-card">
        <h3>Signed Proof</h3>
        <p class="label">Question</p>
        <p>Can compliance/legal verify the proof was issued and not edited?</p>
        <div class="compare">
          <div><span>Certificate</span><strong>{cert_status}</strong></div>
          <div><span>Signature</span><strong>{signature_state}</strong></div>
        </div>
        <p class="result">{'Certificate issued and signature can be verified.' if status == 'certified' else 'Certificate not issued yet.'}</p>
      </div>
    </section>

    <section class="actions">
      {_action_buttons(incident_id, status)}
    </section>
    """


def _page(content: str) -> str:
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Notary Forensic Control Center</title>
  <style>
    :root {{
      --bg: #070b12;
      --panel: #0d1320;
      --panel2: #111827;
      --line: #1f2a3d;
      --text: #e5eefc;
      --muted: #8fa3bf;
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
        radial-gradient(circle at top left, rgba(56,189,248,.14), transparent 32rem),
        radial-gradient(circle at top right, rgba(167,139,250,.11), transparent 30rem),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    a {{ color: var(--blue); text-decoration: none; }}
    .shell {{ max-width: 1280px; margin: 0 auto; padding: 28px; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:24px; }}
    .brand {{ font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--blue); }}
    .subnav a, .subnav form {{ display:inline-block; margin-left:12px; }}
    button, .link-button {{
      border: 0; border-radius: 10px; padding: 10px 14px; font-weight: 700;
      cursor: pointer; background: #1f2937; color: var(--text);
    }}
    button.primary, .primary {{ background: linear-gradient(135deg, #06b6d4, #3b82f6); color: white; }}
    .secondary {{ background: #172033; color: var(--text); border: 1px solid var(--line); }}
    .case-header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:24px; margin-bottom:22px; }}
    .eyebrow {{ color: var(--blue); text-transform:uppercase; font-size:12px; letter-spacing:.14em; font-weight:800; }}
    h1 {{ margin: 4px 0 8px; font-size: 44px; }}
    .subtitle {{ color: var(--muted); margin: 0; max-width: 760px; }}
    .header-badges {{ display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; }}
    .badge {{ display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.05em; }}
    .pending {{ background: rgba(245,158,11,.16); color: #fbbf24; border:1px solid rgba(245,158,11,.35); }}
    .info {{ background: rgba(56,189,248,.15); color: var(--blue); border:1px solid rgba(56,189,248,.35); }}
    .success {{ background: rgba(34,197,94,.15); color: var(--green); border:1px solid rgba(34,197,94,.35); }}
    .certified, .sealed, .method {{ background: rgba(167,139,250,.15); color: var(--purple); border:1px solid rgba(167,139,250,.35); }}
    .workspace {{ display:grid; grid-template-columns: 1fr 360px; gap:18px; margin-bottom:18px; }}
    .graph-panel, .evidence-panel, .proof-card, .empty, .timeline, .actions {{
      background: rgba(13,19,32,.88); border:1px solid var(--line); border-radius: 18px;
      box-shadow: 0 24px 80px rgba(0,0,0,.32); backdrop-filter: blur(8px);
    }}
    .graph-panel {{ padding:18px; }}
    .evidence-panel {{ padding:18px; }}
    .panel-title {{ font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.12em; font-weight:800; margin-bottom:14px; }}
    .graph {{ width:100%; min-height:360px; }}
    .edge {{ stroke: var(--blue); stroke-width: 4; marker-end: url(#arrow); opacity:.72; }}
    .edge.danger {{ stroke: var(--red); }}
    .node rect {{ fill:#101827; stroke:#2e405f; stroke-width:2; filter: drop-shadow(0 0 18px rgba(56,189,248,.08)); }}
    .node text {{ fill: var(--text); font-size:18px; font-weight:800; }}
    .node .small {{ fill: var(--muted); font-size:14px; font-weight:600; }}
    .node.evidence rect {{ stroke: var(--blue); }}
    .node.failure rect {{ stroke: var(--red); fill:#1a1117; filter: drop-shadow(0 0 20px rgba(239,68,68,.2)); }}
    .decision {{ fill:#fecaca !important; font-size:30px !important; }}
    .danger-text {{ fill:#fca5a5 !important; }}
    .meaning {{ color: var(--muted); border-top:1px solid var(--line); padding-top:14px; }}
    .detail-row {{ display:flex; justify-content:space-between; gap:12px; padding:12px 0; border-bottom:1px solid var(--line); }}
    .detail-row span {{ color: var(--muted); }}
    code {{ color: #93c5fd; font-size:12px; }}
    .timeline {{ display:grid; grid-template-columns: repeat(4, 1fr); gap:0; margin-bottom:18px; overflow:hidden; }}
    .step {{ display:flex; gap:12px; padding:18px; align-items:center; border-right:1px solid var(--line); }}
    .step:last-child {{ border-right:0; }}
    .dot {{ width:14px; height:14px; border-radius:50%; background:#334155; box-shadow:0 0 0 4px rgba(51,65,85,.18); }}
    .step.done .dot {{ background: var(--green); box-shadow:0 0 0 4px rgba(34,197,94,.18); }}
    .step-name {{ font-weight:800; }}
    .step-sub {{ color: var(--muted); font-size:13px; }}
    .proof-grid {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:18px; margin-bottom:18px; }}
    .proof-card {{ padding:18px; }}
    .proof-card h3 {{ margin:0 0 10px; }}
    .label {{ color: var(--blue); text-transform:uppercase; font-size:12px; font-weight:900; letter-spacing:.1em; }}
    .compare {{ display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin:14px 0; }}
    .compare div {{ background:#0b1120; border:1px solid var(--line); border-radius:12px; padding:12px; }}
    .compare span {{ display:block; color: var(--muted); font-size:12px; margin-bottom:4px; }}
    .compare strong {{ display:block; overflow-wrap:anywhere; }}
    .result {{ color: var(--muted); }}
    .actions {{ padding:18px; margin-bottom:20px; }}
    .hint {{ color: var(--muted); margin-bottom:0; }}
    .case-list {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:12px; margin-top:18px; }}
    .case-card {{ display:block; background:#0d1320; border:1px solid var(--line); border-radius:14px; padding:14px; color:var(--text); }}
    .case-id {{ font-weight:900; margin-bottom:8px; }}
    .case-meta, .hash {{ color: var(--muted); font-size:13px; margin-top:8px; }}
    .empty {{ padding:30px; text-align:center; }}
    @media(max-width: 920px) {{
      .workspace, .proof-grid, .timeline {{ grid-template-columns: 1fr; }}
      .step {{ border-right:0; border-bottom:1px solid var(--line); }}
    }}
  </style>
  <script>
    function replay(id) {{
      fetch('/v1/incidents/' + id + '/replay', {{method:'POST'}}).then(() => location.reload());
    }}
    function applyFix(id) {{
      fetch('/v1/incidents/' + id + '/mutation', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{fix_config:{{threshold:620}}, expected_correct_behavior:'APPROVE'}})
      }}).then(() => location.reload());
    }}
    function issueCert(id) {{
      fetch('/v1/certificates/' + id, {{method:'POST'}}).then(() => location.reload());
    }}
  </script>
</head>
<body>
  <div class="shell">
    <nav class="topbar">
      <div class="brand">NOTARY · FORENSICS</div>
      <div class="subnav">
        <a href="/dashboard">Dashboard</a>
        <a href="/health">Health</a>
        <form method="post" action="/v1/demo/lending-seed">
          <button class="secondary" type="submit">Seed Lending Demo</button>
        </form>
      </div>
    </nav>
    {content}
  </div>
</body>
</html>
    """


@router.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(_page(_control_center(_selected_incident())))


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    incidents = storage.list_incidents()
    selected = incidents[-1] if incidents else None
    cards = "".join(_incident_card(i) for i in incidents)

    content = _control_center(selected)
    if incidents:
        content += f"""
        <section>
          <div class="panel-title">Case files</div>
          <div class="case-list">{cards}</div>
        </section>
        """
    return HTMLResponse(_page(content))


@router.post("/v1/demo/lending-seed", response_class=HTMLResponse)
def seed_lending_demo() -> RedirectResponse:
    set_demo_agent(_lending_agent)
    snap = _make_demo_snapshot()
    storage.create_incident(snap)
    return RedirectResponse(url="/dashboard", status_code=303)
