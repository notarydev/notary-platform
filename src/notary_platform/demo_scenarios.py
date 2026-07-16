"""Demo scenarios for the Phase 1 Forensic Control Center.

These are local, synthetic demo scenarios inspired by real compliance failure modes.
They do not call real external systems, real providers, or real models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from notary_platform.snapshot import CapturedElement, _compute_root_hash, _seal_element

DEMO_SECRET = b"demo-secret-key-32-bytes-long!!!"


@dataclass(frozen=True)
class ScenarioNode:
    node_id: str
    label: str
    kind: str
    detail: str
    payload: dict[str, Any]
    failure: bool = False


@dataclass(frozen=True)
class DemoScenario:
    scenario_id: str
    title: str
    industry: str
    buyer: str
    risk: str
    model_name: str
    model_version: str
    policy_version: str
    temperature: float
    seed: int
    timestamp: str
    external_system: str
    cassette_response: dict[str, Any]
    original_decision: str
    expected_correct_behavior: str
    fix_config: dict[str, Any]
    nodes: list[ScenarioNode]
    # Scenario Intelligence — how the failure pattern was discovered.
    source_corpus: str = ""
    candidate_cluster: str = ""
    pattern: str = ""
    policy_gap: str = ""
    regulatory_mapping: str = ""
    label_source: str = ""
    replayability: str = ""
    release_gate: str = ""

    def agent_decision(self, threshold: int | None = None) -> str:
        """Return the demo agent decision for this scenario."""
        if self.scenario_id == "lending-denial":
            score = int(self.cassette_response["score"])
            actual_threshold = threshold if threshold is not None else int(
                self.nodes[-2].payload["threshold"]
            )
            return "APPROVE" if score >= actual_threshold else "DENY"

        if self.scenario_id == "prior-auth-denial":
            require_human_review = bool(
                self.fix_config.get("require_human_review_for_high_risk_note")
                if threshold is None
                else True
            )
            if require_human_review:
                return "ESCALATE_TO_HUMAN_REVIEW"
            return "DENY"

        if self.scenario_id == "hiring-screen-rejection":
            remove_age_proxy = bool(
                self.fix_config.get("remove_age_proxy")
                if threshold is None
                else True
            )
            if remove_age_proxy:
                return "ADVANCE_TO_REVIEW"
            return "REJECT"

        if self.scenario_id == "customer-service-handoff":
            human_request_count = int(
                self.cassette_response.get("human_request_count", 0)
            )
            negative_sentiment = str(self.cassette_response.get("sentiment", "")).lower() == "negative"
            enforce = bool(
                self.fix_config.get("escalate_after_repeated_human_request")
                if threshold is None
                else True
            )
            if enforce and (human_request_count >= 2 or negative_sentiment):
                return "ESCALATE_TO_HUMAN"
            return "CONTINUE_BOT"

        return self.original_decision


SCENARIOS: dict[str, DemoScenario] = {
    "customer-service-handoff": DemoScenario(
        scenario_id="customer-service-handoff",
        title="Customer-service failed handoff",
        industry="Customer Support / Contact Center",
        buyer="Support engineering, CX compliance, Trust & Safety",
        risk=(
            "Customer-harm risk: frustrated customer repeatedly asks for a human while the bot"
            " keeps responding, instead of escalating per policy."
        ),
        model_name="Support Agent with support-escalation-policy-v3",
        model_version="support-agent-2025.06",
        policy_version="support-escalation-policy-v3",
        temperature=0.2,
        seed=515029,
        timestamp="2025-07-15T00:00:00Z",
        external_system="Chat transcript / intent-classifier",
        cassette_response={
            "channel": "chat",
            "intent": "billing dispute",
            "sentiment": "negative",
            "human_request_count": 3,
        },
        original_decision="CONTINUE_BOT",
        expected_correct_behavior="ESCALATE_TO_HUMAN",
        fix_config={"escalate_after_repeated_human_request": True},
        source_corpus="12,482 AI support conversations",
        candidate_cluster="184 similar failed handoffs",
        pattern="repeated human request + negative sentiment + bot continued",
        policy_gap=(
            "escalation-policy-v3 requires escalation after 2 human requests or negative"
            " sentiment"
        ),
        regulatory_mapping="Support SLA / CX escalation policy",
        label_source="QA lead / demo label",
        replayability="fully replayable from sealed cassette",
        release_gate="added to support-agent release suite",
        nodes=[
            ScenarioNode(
                "conversation",
                "Chat Conversation",
                "input",
                "Customer opens a billing-dispute chat with negative sentiment.",
                {
                    "channel": "chat",
                    "intent": "billing dispute",
                    "sentiment": "negative",
                    "human_request_count": 3,
                },
            ),
            ScenarioNode(
                "intent-classifier",
                "Intent Classifier",
                "tool",
                "Cassette records the classified intent and sentiment.",
                {
                    "endpoint": "POST /intent",
                    "response": {"intent": "billing dispute", "sentiment": "negative"},
                },
            ),
            ScenarioNode(
                "support-agent",
                "Support Agent",
                "model",
                "Model handles the chat under the support escalation policy.",
                {"model": "support-agent-2025.06", "temperature": 0.2},
            ),
            ScenarioNode(
                "escalation-rule",
                "Escalation Rule",
                "rule",
                "Original workflow allowed the bot to keep responding past 3 human requests.",
                {"escalate_after_human_request": False},
                failure=True,
            ),
            ScenarioNode(
                "decision",
                "Final Decision",
                "decision",
                "Agent continues the bot conversation instead of escalating.",
                {"decision": "CONTINUE_BOT"},
            ),
        ],
    ),
    "lending-denial": DemoScenario(
        scenario_id="lending-denial",
        title="Qualified borrower denied",
        industry="Lending / Fintech",
        buyer="Chief Compliance Officer, Fair Lending team, General Counsel",
        risk="Fair lending / ECOA risk: qualified applicant denied by threshold logic.",
        model_name="Claude 3.5 Sonnet via lending-agent-policy-v1",
        model_version="claude-3-5-sonnet-20240620",
        policy_version="credit-policy-v2025.07",
        temperature=0.0,
        seed=104729,
        timestamp="2025-07-15T00:00:00Z",
        external_system="Credit Bureau API /score",
        cassette_response={"score": 650},
        original_decision="DENY",
        expected_correct_behavior="APPROVE",
        fix_config={"threshold": 620},
        source_corpus="9,310 lending underwriting decisions",
        candidate_cluster="142 challenged denials",
        pattern="borderline score + rigid threshold + no human review",
        policy_gap="credit-policy-v2025.07 denies at fixed 700 threshold with no override path",
        regulatory_mapping="ECOA / Fair Lending",
        label_source="Fair Lending team / demo label",
        replayability="fully replayable from sealed cassette",
        release_gate="added to lending-agent release suite",
        nodes=[
            ScenarioNode(
                "application",
                "Loan Application",
                "input",
                "Applicant A-1027 requests underwriting decision.",
                {"applicant_id": "A-1027", "loan_type": "personal_loan"},
            ),
            ScenarioNode(
                "policy",
                "Policy Prompt",
                "model",
                "Model receives fair-lending policy context and threshold rule.",
                {"model": "claude-3-5-sonnet-20240620", "temperature": 0.0},
            ),
            ScenarioNode(
                "credit-api",
                "Credit Score API",
                "tool",
                "Recorded cassette response returns score 650.",
                {"endpoint": "POST /score", "response": {"score": 650}},
            ),
            ScenarioNode(
                "threshold",
                "Decision Threshold",
                "rule",
                "Original policy threshold is 700.",
                {"threshold": 700},
                failure=True,
            ),
            ScenarioNode(
                "decision",
                "Final Decision",
                "decision",
                "Agent denies the borrower.",
                {"decision": "DENY"},
            ),
        ],
    ),
    "prior-auth-denial": DemoScenario(
        scenario_id="prior-auth-denial",
        title="Necessary care auto-denied",
        industry="Healthcare / Insurance",
        buyer="Clinical compliance, utilization management, legal",
        risk="Clinical-review risk: high-risk physician note was auto-denied instead of escalated.",
        model_name="PriorAuthReview Agent with clinical-policy-rag-v2",
        model_version="claude-3-haiku-20240307",
        policy_version="medical-necessity-policy-2025.04",
        temperature=0.1,
        seed=271828,
        timestamp="2025-07-15T00:05:00Z",
        external_system="Patient History API /episode-summary",
        cassette_response={"risk_score": "high", "physician_note": "continued skilled care required"},
        original_decision="DENY",
        expected_correct_behavior="ESCALATE_TO_HUMAN_REVIEW",
        fix_config={"require_human_review_for_high_risk_note": True},
        source_corpus="7,844 prior-auth determinations",
        candidate_cluster="96 auto-denials with high-risk notes",
        pattern="high-risk physician note + auto-denial without escalation",
        policy_gap="medical-necessity-policy-2025.04 allows auto-denial despite high-risk note",
        regulatory_mapping="CMS medical necessity / utilization management",
        label_source="Clinical compliance / demo label",
        replayability="fully replayable from sealed cassette",
        release_gate="added to prior-auth-agent release suite",
        nodes=[
            ScenarioNode(
                "request",
                "Prior Auth Request",
                "input",
                "Request for post-acute care extension.",
                {"member_id": "M-4481", "care_type": "post_acute"},
            ),
            ScenarioNode(
                "clinical-policy",
                "Clinical Policy",
                "model",
                "Model applies medical-necessity policy.",
                {"model": "claude-3-haiku-20240307", "temperature": 0.1},
            ),
            ScenarioNode(
                "patient-history",
                "Patient History API",
                "tool",
                "Cassette contains high-risk physician-note evidence.",
                {"endpoint": "GET /episode-summary", "response": {"risk_score": "high"}},
            ),
            ScenarioNode(
                "utilization-rule",
                "Utilization Rule",
                "rule",
                "Original workflow allowed auto-denial despite high-risk note.",
                {"human_review_required": False},
                failure=True,
            ),
            ScenarioNode(
                "decision",
                "Final Decision",
                "decision",
                "Agent denies care authorization.",
                {"decision": "DENY"},
            ),
        ],
    ),
    "hiring-screen-rejection": DemoScenario(
        scenario_id="hiring-screen-rejection",
        title="Qualified candidate rejected",
        industry="Hiring / HR Compliance",
        buyer="HR compliance, employment counsel, AI governance",
        risk="Employment discrimination risk: candidate rejected through age-proxy feature.",
        model_name="ResumeRanker Agent with hiring-policy-v3",
        model_version="gpt-4o-mini-2024-07-18",
        policy_version="hiring-screen-policy-2025.02",
        temperature=0.0,
        seed=314159,
        timestamp="2025-07-15T00:10:00Z",
        external_system="Resume Parser /candidate-features",
        cassette_response={"years_experience": 28, "seniority_proxy": "age_over_55_likely"},
        original_decision="REJECT",
        expected_correct_behavior="ADVANCE_TO_REVIEW",
        fix_config={"remove_age_proxy": True, "route_borderline_to_human_review": True},
        source_corpus="6,127 screened candidates",
        candidate_cluster="73 rejected candidates with proxy-risk pattern",
        pattern="age-proxy feature + borderline score + rejection",
        policy_gap="hiring-screen-policy-2025.02 used seniority proxy in rejection score",
        regulatory_mapping="EEOC / employment discrimination",
        label_source="HR compliance / demo label",
        replayability="fully replayable from sealed cassette",
        release_gate="added to hiring-agent release suite",
        nodes=[
            ScenarioNode(
                "resume",
                "Resume",
                "input",
                "Candidate has required qualifications and long work history.",
                {"candidate_id": "C-9021", "role": "senior_support_specialist"},
            ),
            ScenarioNode(
                "parser",
                "Resume Parser",
                "tool",
                "Cassette records extracted experience and proxy feature.",
                {"endpoint": "POST /candidate-features", "response": {"years_experience": 28}},
            ),
            ScenarioNode(
                "ranker",
                "Ranking Model",
                "model",
                "Model ranks candidate under hiring policy.",
                {"model": "gpt-4o-mini-2024-07-18", "temperature": 0.0},
            ),
            ScenarioNode(
                "age-proxy",
                "Age Proxy Rule",
                "rule",
                "Original workflow used seniority proxy in rejection score.",
                {"seniority_proxy": "age_over_55_likely"},
                failure=True,
            ),
            ScenarioNode(
                "decision",
                "Final Decision",
                "decision",
                "Agent rejects the candidate.",
                {"decision": "REJECT"},
            ),
        ],
    ),
}


def get_scenario(scenario_id: str) -> DemoScenario:
    return SCENARIOS.get(scenario_id, SCENARIOS["customer-service-handoff"])


def build_snapshot(scenario: DemoScenario) -> dict[str, Any]:
    """Create a sealed snapshot for a demo scenario."""
    elements: list[dict[str, Any]] = []

    for node in scenario.nodes:
        if node.kind == "tool":
            elements.append(
                {
                    "kind": "http",
                    "payload": {
                        "request": {
                            "method": "POST",
                            "url": f"https://demo.notary.local/{node.node_id}",
                            "body": f'{{"scenario":"{scenario.scenario_id}"}}',
                        },
                        "response": scenario.cassette_response,
                        "status": 200,
                        "node_id": node.node_id,
                    },
                }
            )
        elif node.kind == "model":
            elements.append(
                {
                    "kind": "llm",
                    "payload": {
                        "prompt": node.detail,
                        "response": "Policy context applied.",
                        "metadata": {
                            "model": scenario.model_version,
                            "policy_version": scenario.policy_version,
                            "temperature": scenario.temperature,
                            "seed": scenario.seed,
                            "node_id": node.node_id,
                        },
                    },
                }
            )
        elif node.kind == "decision":
            elements.append(
                {
                    "kind": "decision",
                    "payload": {
                        "decision": scenario.original_decision,
                        "expected_correct_behavior": scenario.expected_correct_behavior,
                        "node_id": node.node_id,
                    },
                }
            )
        else:
            elements.append(
                {
                    "kind": node.kind,
                    "payload": {**node.payload, "node_id": node.node_id},
                }
            )

    prev_hash = b"\x00" * 32
    elem_hashes: list[bytes] = []
    sealed: list[dict[str, Any]] = []

    for e in elements:
        ce = CapturedElement(kind=e["kind"], payload=e.get("payload", {}))
        h = _seal_element(prev_hash, ce.canonical_bytes(), DEMO_SECRET)
        elem_hashes.append(h)
        sealed.append({"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()})
        prev_hash = h

    root = _compute_root_hash(elem_hashes)
    return {
        "schema_version": 1,
        "timestamp": scenario.timestamp,
        "scenario_id": scenario.scenario_id,
        "elements": sealed,
        "merkle_chain": [h.hex() for h in elem_hashes],
        "root_hash": root,
    }
