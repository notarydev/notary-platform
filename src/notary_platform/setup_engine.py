"""Decision Assurance Setup Engine.

Deterministic core that compiles a customer's AI decision workflow
into executable Notary configuration: evidence contracts, capture policies,
record selection rules, import previews, replayability assessments,
scenario candidates, and release gate plans.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from notary_platform.models import (
    AssuranceSetupPlan,
    ImportPreview,
    RecordSelectionResult,
    RecordSelectionRule,
    SetupReadinessAssessment,
    WorkflowTemplate,
)

# ── Templates ──

WORKFLOW_TEMPLATES: dict[str, WorkflowTemplate] = {}

def _seed_templates() -> None:
    templates = [
        WorkflowTemplate(
            id="wf-tmpl-refund-policy",
            workflow_type="refund_or_policy_answer",
            name="Refund or Policy Answer",
            description=(
                "An AI support bot answers refund, fare, billing, or policy questions. "
                "The decision is whether to answer directly or escalate to a human."
            ),
            decision_description="Should the AI answer the customer directly or escalate to a human?",
            bad_outcome="The bot offers a refund or policy that does not exist or contradicts the official policy source.",
            expected_safe_outcome="ESCALATE_TO_HUMAN",
            risk_level="high",
            evidence_sources=[
                {"name": "Customer Support Record", "source_type": "customer_support_record", "required": True,
                 "captures": "Customer message, case ID, channel, timestamp, and source ticket reference.",
                 "why_include": "Proves what the customer asked and where the decision happened.",
                 "does_not_capture": "Agent staffing, queue timing, unrelated CRM history."},
                {"name": "Policy Knowledge Source", "source_type": "policy_knowledge_source", "required": True,
                 "captures": "The official policy response or policy version the bot retrieved.",
                 "why_include": "A policy mismatch is the causal evidence for the wrong answer.",
                 "does_not_capture": "Policy authoring workflow or approval chain."},
                {"name": "AI System Output", "source_type": "ai_system_output", "required": True,
                 "captures": "Model call, prompt, response, tool call proposals, and final decision.",
                 "why_include": "This is the decision system being reviewed.",
                 "does_not_capture": "Training data or unrelated model internals."},
                {"name": "Prompt / Policy Config", "source_type": "prompt_policy_config", "required": True,
                 "captures": "Prompt version, routing rule, model configuration, feature flag, and policy version.",
                 "why_include": "The bot must be evaluated against the configuration in force at decision time.",
                 "does_not_capture": "Prompt authoring workflow unless explicitly included."},
                {"name": "Human Review Queue", "source_type": "human_review_queue", "required": False,
                 "captures": "Expected outcome label, human override, reviewer role, approval reason.",
                 "why_include": "Provides the customer-approved answer key for proof.",
                 "does_not_capture": "Reviewer productivity or case assignment."},
                {"name": "Release / CI System", "source_type": "release_ci_system", "required": False,
                 "captures": "Agent version, git commit, build ID, release candidate.",
                 "why_include": "Connects Scenarios to Release Gate checks.",
                 "does_not_capture": "Arbitrary CI metadata."},
            ],
            record_selection_rules=[
                {"trigger_type": "policy_answer", "label": "Bot gives policy/refund/fare answer",
                 "description": "Bot response contains refund, fare, billing, legal, or policy language.", "enabled": True},
                {"trigger_type": "customer_dispute", "label": "Customer disputes bot answer",
                 "description": "Customer replied negatively to bot, opened dispute, or asked for manager.", "enabled": True},
                {"trigger_type": "human_override", "label": "Human agent overrides bot",
                 "description": "Human changed or corrected the outcome the bot produced.", "enabled": True},
                {"trigger_type": "handoff_requested", "label": "Human handoff requested but bot continued",
                 "description": "Customer asked to speak to a human but the bot continued responding.", "enabled": True},
                {"trigger_type": "policy_mismatch", "label": "Bot answer conflicts with policy source",
                 "description": "Policy lookup response contradicts the bot's answer to the customer.", "enabled": True},
                {"trigger_type": "missing_policy_lookup", "label": "Policy lookup missing or failed",
                 "description": "Bot gave a policy answer without retrieving the current policy.", "enabled": True},
                {"trigger_type": "low_confidence", "label": "Low confidence or missing model response",
                 "description": "Bot confidence below threshold or model did not respond.", "enabled": True},
                {"trigger_type": "sample", "label": "Random sample of normal conversations",
                 "description": "Sample 0.1% of conversations that matched no other rule.", "enabled": False},
            ],
        ),
        WorkflowTemplate(
            id="wf-tmpl-lending",
            workflow_type="lending_decision",
            name="Lending Decision",
            description="An AI model approves, denies, or escalates loan applications based on applicant data and credit bureau information.",
            decision_description="Approve, deny, or review this loan?",
            bad_outcome="The model approves a loan that should have been denied or denies one that should have been approved due to incorrect reasoning.",
            expected_safe_outcome="REVIEW_ESCALATION",
            risk_level="high",
            evidence_sources=[
                {"name": "Loan Application Record", "source_type": "loan_application", "required": True,
                 "captures": "Application data, applicant details, loan amount, purpose.",
                 "why_include": "The decision is based on this application.",
                 "does_not_capture": "Applicant credit history not used in decision."},
                {"name": "Credit Bureau Response", "source_type": "credit_bureau_response", "required": True,
                 "captures": "Bureau data, credit score, tradelines, and inquiry record.",
                 "why_include": "Credit data is a primary input to the decision.",
                 "does_not_capture": "Full credit report beyond what was used."},
                {"name": "Underwriting Policy Config", "source_type": "underwriting_policy", "required": True,
                 "captures": "Policy version, risk tiers, rules applied.",
                 "why_include": "The decision must be evaluated against policy in force.",
                 "does_not_capture": "Policy draft history."},
                {"name": "AI System Output", "source_type": "ai_system_output", "required": True,
                 "captures": "Model call, score, decision, and reason codes.",
                 "why_include": "This is the decision system under review.",
                 "does_not_capture": "Training data or model internals."},
            ],
        ),
        WorkflowTemplate(
            id="wf-tmpl-escalation",
            workflow_type="support_escalation",
            name="Support Escalation",
            description="An AI triage bot decides whether to escalate a support conversation to a human agent or handle it automatically.",
            decision_description="Should this chat escalate to a human?",
            bad_outcome="The bot fails to escalate a conversation that requires human intervention.",
            expected_safe_outcome="ESCALATE_TO_HUMAN",
            risk_level="medium",
            evidence_sources=[
                {"name": "Conversation Transcript", "source_type": "conversation_transcript", "required": True,
                 "captures": "Full conversation text, customer intent, sentiment.",
                 "why_include": "Proves what the customer needed.", "does_not_capture": "Agent notes."},
                {"name": "Escalation Policy Config", "source_type": "escalation_policy", "required": True,
                 "captures": "Escalation rules, thresholds, override conditions.",
                 "why_include": "Determines if bot followed escalation rules.",
                 "does_not_capture": "Agent availability."},
                {"name": "AI System Output", "source_type": "ai_system_output", "required": True,
                 "captures": "Model call, classification, confidence, decision.",
                 "why_include": "This is the decision system under review.",
                 "does_not_capture": "Training data."},
            ],
        ),
        WorkflowTemplate(
            id="wf-tmpl-claims",
            workflow_type="insurance_claim_triage",
            name="Insurance Claim Triage",
            description="An AI system triages insurance claims: pay, deny, or escalate for manual review.",
            decision_description="Pay, deny, or escalate this claim?",
            bad_outcome="The AI denies a valid claim or approves a fraudulent one.",
            expected_safe_outcome="ESCALATE_TO_HUMAN",
            risk_level="high",
            evidence_sources=[
                {"name": "Claim Record", "source_type": "claim_record", "required": True,
                 "captures": "Claim details, policy holder, incident description, amount.",
                 "why_include": "The claim is the subject of the decision.",
                 "does_not_capture": "Unrelated claims history."},
                {"name": "Policy Rules Config", "source_type": "policy_rules_config", "required": True,
                 "captures": "Coverage rules, exclusions, limits, policy version.",
                 "why_include": "The decision must match policy coverage.",
                 "does_not_capture": "Policy authoring."},
                {"name": "AI System Output", "source_type": "ai_system_output", "required": True,
                 "captures": "Model call, triage score, decision, reason codes.",
                 "why_include": "This is the decision system under review.",
                 "does_not_capture": "Training data."},
            ],
        ),
        WorkflowTemplate(
            id="wf-tmpl-hiring",
            workflow_type="hiring_screening",
            name="Hiring Screening",
            description="An AI model screens job candidates and recommends advance, reject, or escalate to human review.",
            decision_description="Advance this candidate to review?",
            bad_outcome="The AI rejects a qualified candidate due to bias or incorrect screening logic.",
            expected_safe_outcome="ESCALATE_TO_HUMAN",
            risk_level="high",
            evidence_sources=[
                {"name": "Candidate Application", "source_type": "candidate_application", "required": True,
                 "captures": "Resume, application, skills, experience.",
                 "why_include": "The candidate data the AI evaluated.",
                 "does_not_capture": "Demographic data not used in screening."},
                {"name": "Screening Rules Config", "source_type": "screening_rules", "required": True,
                 "captures": "Screening criteria, weightings, thresholds, policy version.",
                 "why_include": "Rules define what the AI should look for.",
                 "does_not_capture": "Hiring manager preferences."},
                {"name": "AI System Output", "source_type": "ai_system_output", "required": True,
                 "captures": "Model call, score, decision, reason codes.",
                 "why_include": "This is the decision system under review.",
                 "does_not_capture": "Training data."},
            ],
        ),
    ]
    for t in templates:
        WORKFLOW_TEMPLATES[t.workflow_type] = t

_seed_templates()


def get_workflow_templates() -> list[dict]:
    return [t.to_dict() for t in WORKFLOW_TEMPLATES.values()]


def get_workflow_template(wf_type: str) -> dict | None:
    t = WORKFLOW_TEMPLATES.get(wf_type)
    return t.to_dict() if t else None


# ── Engine Services ──

class AssuranceSetupService:
    """Owns setup plan lifecycle."""

    def __init__(self, storage: Any) -> None:
        self._storage = storage

    def create_plan(self, org_id: str, environment_id: str, objective: str = "",
                    workflow_type: str = "", workflow_name: str = "") -> AssuranceSetupPlan:
        plan = AssuranceSetupPlan(
            id=f"plan-{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            environment_id=environment_id,
            objective=objective,
            workflow_type=workflow_type,
            workflow_name=workflow_name,
            status="draft",
            current_step=0,
        )
        self._storage.save_assurance_plan(plan)
        return plan

    def get_plan(self, plan_id: str) -> AssuranceSetupPlan | None:
        return self._storage.get_assurance_plan(plan_id)

    def get_all_plans(self, org_id: str) -> list[AssuranceSetupPlan]:
        return self._storage.list_assurance_plans(org_id)

    def update_plan(self, plan_id: str, **updates: Any) -> AssuranceSetupPlan | None:
        plan = self._storage.get_assurance_plan(plan_id)
        if not plan:
            return None
        for k, v in updates.items():
            if hasattr(plan, k) and k not in ("id", "org_id", "created_at"):
                setattr(plan, k, v)
        plan.touch()
        self._storage.save_assurance_plan(plan)
        return plan


class EvidenceContractService:
    """Recommends and validates evidence fields per workflow type."""

    NORTHSTAR_EVIDENCE = {
        "required": [
            {"field": "customer_request", "label": "Customer request / conversation transcript",
             "why": "Proves what the customer actually asked."},
            {"field": "ai_response", "label": "AI / bot response",
             "why": "Proves what the AI told the customer."},
            {"field": "policy_lookup_response", "label": "Policy lookup response",
             "why": "Proves whether the answer matched official policy."},
            {"field": "final_decision", "label": "Final decision classification",
             "why": "Required to classify what the AI actually did."},
            {"field": "prompt_policy_config", "label": "Prompt / policy config version",
             "why": "Proves what instructions governed the agent at decision time."},
            {"field": "agent_version", "label": "Agent version / release ID",
             "why": "Required to compare old and fixed releases."},
            {"field": "expected_outcome_label", "label": "Expected outcome label",
             "why": "Notary does not decide correctness; the customer labels it."},
        ],
        "optional": [
            {"field": "full_transcript", "label": "Full conversation transcript",
             "why": "Provides complete context for policy disputes."},
            {"field": "human_resolution_notes", "label": "Human resolution notes",
             "why": "Documents how the human resolved the case."},
            {"field": "confidence_score", "label": "AI confidence score",
             "why": "Helps identify low-confidence decisions for review."},
            {"field": "handoff_event", "label": "Human handoff event",
             "why": "Captures when and why handoff occurred."},
            {"field": "customer_dispute_reason", "label": "Customer dispute reason",
             "why": "Classifies why the customer disputed the AI answer."},
        ],
        "excluded": [
            {"field": "queue_wait_time", "label": "Queue wait time", "why": "Not decision evidence."},
            {"field": "agent_productivity", "label": "Agent productivity metrics", "why": "Not decision evidence."},
            {"field": "csat_score", "label": "CSAT / NPS score", "why": "Outcome metric, not decision evidence."},
            {"field": "full_crm_history", "label": "Full CRM history", "why": "Contains unrelated customer data."},
            {"field": "marketing_segments", "label": "Marketing segments", "why": "Not needed for decision assurance."},
            {"field": "infrastructure_metrics", "label": "Infrastructure / server metrics", "why": "Operational data, not evidence."},
        ],
    }

    def recommend(self, plan: AssuranceSetupPlan) -> dict:
        """Return evidence contract recommendation based on workflow type."""
        wf_type = plan.workflow_type or "refund_or_policy_answer"
        template = WORKFLOW_TEMPLATES.get(wf_type)
        if not template:
            return self.NORTHSTAR_EVIDENCE
        required = []
        optional = []
        excluded = []
        for src in template.evidence_sources:
            entry = {"field": src["source_type"], "label": src["name"],
                     "why": src.get("why_include", ""),
                     "captures": src.get("captures", ""),
                     "does_not_capture": src.get("does_not_capture", "")}
            if src.get("required"):
                required.append(entry)
            else:
                optional.append(entry)
        for entry in self.NORTHSTAR_EVIDENCE["excluded"]:
            excluded.append(entry)
        return {"required": required, "optional": optional, "excluded": excluded}


class CapturePolicyService:
    """Defines live capture rules and recommendations."""

    def recommend(self, plan: AssuranceSetupPlan, systems: list[dict] | None = None) -> list[dict]:
        """Recommend capture methods based on available systems."""
        methods = []
        methods.append({
            "method": "sdk",
            "label": "Python SDK",
            "recommended": True,
            "best_for": "Instrumented Python AI agents",
            "captures": "LLM calls, tool calls, decisions, and sealed cassettes in-process",
            "snippet_type": "python",
        })
        methods.append({
            "method": "api",
            "label": "API Submission",
            "recommended": True,
            "best_for": "Backend systems sending Verification Records directly",
            "captures": "Structured decision evidence, labels, and references",
            "snippet_type": "curl",
        })
        if systems:
            for sys in systems:
                if sys.get("source_type") in ("ticketing", "crm", "servicenow", "zendesk", "salesforce"):
                    methods.append({
                        "method": "webhook",
                        "label": f"Webhook — {sys.get('name', 'Source system')}",
                        "recommended": True,
                        "best_for": f"Event forwarding from {sys.get('name')}",
                        "captures": "Events that represent a decision or escalation",
                        "snippet_type": "webhook",
                    })
        methods.append({
            "method": "import",
            "label": "Batch / Log Import",
            "recommended": True,
            "best_for": "Existing decision logs, historical conversations, CSV/JSON exports",
            "captures": "Verification Records created from imported data",
            "snippet_type": "json",
        })
        methods.append({
            "method": "manual",
            "label": "Manual Submission",
            "recommended": False,
            "best_for": "Complaints, overrides, disputes, or one-off reviews",
            "captures": "Human-provided expected outcome and evidence summary",
            "snippet_type": "form",
        })
        return methods

    def build_policy(self, capture_method: str, plan: AssuranceSetupPlan) -> dict:
        policy = {
            "capture_method": capture_method,
            "triggers": [],
            "sampling": {"normal": 0.001},
            "redaction": {"email": "hash", "payment_card": "omit"},
            "submit_mode": "on_trigger",
            "max_record_size_mb": 10,
        }
        template = WORKFLOW_TEMPLATES.get(plan.workflow_type)
        if template:
            policy["triggers"] = [r["trigger_type"] for r in template.record_selection_rules if r.get("enabled")]
        return policy


class RecordSelectionService:
    """Applies rules to events/logs and decides what to capture."""

    def apply_rules(self, records: list[dict], rules: list[RecordSelectionRule]) -> list[RecordSelectionResult]:
        results = []
        for i, rec in enumerate(records):
            result = RecordSelectionResult(
                id=f"rsr-{uuid.uuid4().hex[:12]}",
                plan_id="",
                source_row_id=rec.get("source_record_ref", f"row-{i}"),
                decision="ignore",
                create_vr=False,
            )
            elements = rec.get("elements", [])
            text = json.dumps(rec).lower()
            matched = []
            for rule in rules:
                if not rule.enabled:
                    continue
                rule_type = rule.trigger_type
                if rule_type == "policy_answer" and any(k in text for k in ("refund", "fare", "policy", "billing", "legal")):
                    matched.append(rule.id)
                elif rule_type == "customer_dispute" and any(k in text for k in ("wrong", "incorrect", "dispute", "complaint", "manager")):
                    matched.append(rule.id)
                elif rule_type == "human_override" and any(k in text for k in ("override", "human changed", "corrected")):
                    matched.append(rule.id)
                elif rule_type == "handoff_requested" and any(k in text for k in ("human", "agent", "speak to", "escalate")):
                    matched.append(rule.id)
                elif rule_type == "policy_mismatch" and "policy" in text and any(k in text for k in ("contradict", "conflict", "mismatch")):
                    matched.append(rule.id)
                elif rule_type == "missing_policy_lookup" and "policy" in text and "lookup" not in text:
                    matched.append(rule.id)
                elif rule_type == "low_confidence" and any(k in text for k in ("confidence", "uncertain", "low score")):
                    matched.append(rule.id)
                elif rule_type == "sample":
                    if i % 1000 == 0:
                        matched.append(rule.id)
                if matched:
                    break
            if matched:
                has_decision = any(e.get("kind") == "decision" for e in elements)
                if has_decision:
                    result.decision = "capture"
                    result.create_vr = True
                    result.trigger = rule.trigger_type if matched else "unknown"
                    result.matched_rules = matched
                    result.reason = f"Matched trigger: {result.trigger}"
                    has_cassette = any(e.get("kind") in ("tool", "llm", "http") for e in elements)
                    has_expected = bool(rec.get("expected_outcome"))
                    if has_cassette and has_expected:
                        result.replayability = "replayable"
                    elif has_cassette and not has_expected:
                        result.replayability = "requires_human_label"
                    elif not has_cassette and has_expected:
                        result.replayability = "missing_context"
                    else:
                        result.replayability = "evidence_only"
                    prev = results[-1] if results else None
                    if prev and prev.replayability == "replayable" and prev.trigger == result.trigger:
                        result.scenario_candidate = True
            results.append(result)
        return results


class ImportPreviewService:
    """Runs preview before committing import."""

    NORTHSTAR_VOLUME = {
        "monthly_conversations": 1_000_000,
        "policy_related": 18_400,
        "high_risk_matched": 1_284,
        "replayable": 612,
        "needs_label": 401,
        "missing_cassette": 173,
        "evidence_only": 98,
        "scenario_candidates": 47,
    }

    def preview(self, records: list[dict], rules: list[RecordSelectionRule],
                field_mapping: dict | None = None) -> ImportPreview:
        svc = RecordSelectionService()
        results = svc.apply_rules(records, rules) if rules else []
        matched = [r for r in results if r.decision == "capture"]
        total = len(records)
        sample_records = []
        for r in results[:10]:
            sample_records.append({
                "source_record_ref": r.source_row_id,
                "decision": r.decision,
                "trigger": r.trigger,
                "replayability": r.replayability,
                "scenario_candidate": r.scenario_candidate,
            })
        return ImportPreview(
            total_records=total,
            matched_count=len(matched),
            replayable_count=len([r for r in matched if r.replayability == "replayable"]),
            needs_label_count=len([r for r in matched if r.replayability == "requires_human_label"]),
            missing_cassette_count=len([r for r in matched if r.replayability == "missing_context"]),
            evidence_only_count=len([r for r in matched if r.replayability == "evidence_only"]),
            scenario_candidate_count=len([r for r in matched if r.scenario_candidate]),
            sample_records=sample_records,
        )

    def estimate_volume(self, workflow_type: str) -> dict:
        return self.NORTHSTAR_VOLUME


class ReplayabilityService:
    """Classifies every record's replay readiness."""

    def assess(self, record: dict) -> dict:
        elements = record.get("elements", [])
        has_input = any(e.get("kind") == "input" for e in elements)
        has_decision = any(e.get("kind") == "decision" for e in elements)
        has_cassette = any(e.get("kind") in ("tool", "llm", "http") for e in elements)
        has_expected = bool(record.get("expected_outcome"))
        has_config = bool(record.get("agent_version") or record.get("prompt_version"))

        missing = []
        if not has_input:
            missing.append("customer_input")
        if not has_decision:
            missing.append("decision_output")
        if not has_cassette:
            missing.append("replay_cassette")
        if not has_expected:
            missing.append("expected_outcome")
        if not has_config:
            missing.append("agent_version")

        if has_input and has_decision and has_cassette and has_expected and has_config:
            return {"replayability": "replayable", "missing_prerequisites": []}
        if has_input and has_decision and has_cassette and not has_expected:
            return {"replayability": "requires_human_label", "missing_prerequisites": missing}
        if has_input and has_decision and not has_cassette:
            return {"replayability": "missing_context", "missing_prerequisites": missing}
        if has_input and not has_decision:
            return {"replayability": "evidence_only", "missing_prerequisites": missing}
        return {"replayability": "blocked", "missing_prerequisites": missing}


class ScenarioCandidateService:
    """Creates and groups scenario candidates."""

    def recommend_from_records(self, records: list[dict]) -> list[dict]:
        groups: dict[str, list[dict]] = {}
        for rec in records:
            trigger = rec.get("trigger", "unknown")
            if trigger not in groups:
                groups[trigger] = []
            groups[trigger].append(rec)
        candidates = []
        for trigger, group in groups.items():
            if len(group) < 2:
                continue
            candidates.append({
                "title": self._title_for_trigger(trigger),
                "trigger": trigger,
                "record_count": len(group),
                "sample_record_ids": [r.get("id", "") for r in group[:3]],
                "replayable_count": len([r for r in group if r.get("replayability") == "replayable"]),
                "needs_label_count": len([r for r in group if r.get("replayability") == "requires_human_label"]),
                "missing_context_count": len([r for r in group if r.get("replayability") == "missing_context"]),
            })
        return candidates

    def _title_for_trigger(self, trigger: str) -> str:
        titles = {
            "policy_answer": "Policy hallucination — refund/fare answer",
            "customer_dispute": "Customer dispute — incorrect AI answer",
            "human_override": "Human override of AI decision",
            "handoff_requested": "Failed handoff — bot continued after escalation",
            "policy_mismatch": "Policy mismatch — bot contradicted policy source",
            "missing_policy_lookup": "Missing policy source — answer without authority",
            "low_confidence": "Low confidence decision needing review",
            "sample": "Normal conversation sample",
        }
        return titles.get(trigger, f"Pattern: {trigger}")


class ReleaseGatePlanner:
    """Recommends readiness policy from scenarios."""

    def recommend(self, scenarios: list[dict]) -> dict:
        required = []
        for s in scenarios:
            required.append({"scenario_id": s.get("id", ""), "title": s.get("business_title", s.get("title", "Scenario"))})
        return {
            "policy_name": "High-Risk Decision Policy Gate",
            "required_scenarios": required,
            "pass_condition": "all_pass",
            "failure_behavior": "block_release",
        }


class SetupReadinessService:
    """Determines overall setup readiness."""

    def assess(self, plan: AssuranceSetupPlan, storage: Any) -> SetupReadinessAssessment:
        assessment = SetupReadinessAssessment(plan_id=plan.id)
        missing = []
        next_actions = []

        if not plan.objective:
            missing.append("assurance_objective")
            next_actions.append("Define what you need to prove.")
        if not plan.workflow_id:
            missing.append("decision_workflow")
            next_actions.append("Define the AI decision workflow.")
        else:
            wf = storage.get_decision_workflow(plan.workflow_id)
            if wf:
                assessment.can_create_records = True

        if not plan.ai_system_id:
            missing.append("ai_system")
            next_actions.append("Register the AI system making this decision.")
        else:
            assessment.can_create_records = True

        evidence = json.loads(plan.evidence_contract) if isinstance(plan.evidence_contract, str) else plan.evidence_contract
        if not evidence or not evidence.get("required"):
            missing.append("evidence_contract")
            next_actions.append("Define what evidence is required.")
        else:
            assessment.can_create_records = True
            assessment.can_replay = True

        cap = json.loads(plan.capture_policy) if isinstance(plan.capture_policy, str) else plan.capture_policy
        if not cap or not cap.get("capture_method"):
            missing.append("capture_policy")
            next_actions.append("Choose a capture method.")

        if not missing:
            assessment.can_create_records = True
            assessment.can_replay = True
            assessment.can_issue_proof = True
            assessment.can_create_scenarios = True
            assessment.can_create_release_gate = bool(plan.readiness_policy_id)

        assessment.missing_prerequisites = missing
        assessment.next_actions = next_actions
        assessment.estimated_monthly_records = 2100
        assessment.estimated_replayable = 1200
        assessment.estimated_needs_label = 600
        assessment.estimated_storage_gb = 80
        return assessment
