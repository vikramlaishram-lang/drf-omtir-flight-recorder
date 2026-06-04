from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .models import Decision, EvidenceLane, EvidenceRef, ToolResult
from .policy import ActionRule, Policy
from .wal import Wal, sha256_file


ToolHandler = Callable[[dict[str, Any]], ToolResult]


class TypedGateway:
    """Transport-neutral DRF action gate and OMTIR claim-admission boundary."""

    def __init__(self, root: str | Path, policy: Policy, wal: Wal):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.policy = policy
        self.wal = wal
        self.handlers: dict[str, ToolHandler] = {}

    def register_tool(self, action: str, handler: ToolHandler) -> None:
        rule = self.policy.rule_for(action)
        if rule is None:
            raise ValueError(f"Cannot register action without policy rule: {action}")
        if not rule.executable:
            raise ValueError(f"Cannot register non-executable action: {action}")
        self.handlers[action] = handler

    def propose_action(
        self,
        action: str,
        arguments: dict[str, Any],
        *,
        evidence: list[EvidenceRef] | None = None,
        adapted_from_event_id: str | None = None,
    ) -> dict[str, Any]:
        evidence = evidence or []
        event_id = self.wal.next_event_id()
        rule = self.policy.rule_for(action)
        decision, reason = self._action_decision(rule, evidence)
        tool_result: ToolResult | None = None

        if decision == Decision.ALLOW:
            handler = self.handlers.get(action)
            if handler is None:
                decision = Decision.DENY
                reason = "HANDLER_NOT_REGISTERED"
            else:
                try:
                    tool_result = handler(arguments)
                except Exception as exc:  # pragma: no cover - defensive boundary
                    decision = Decision.DENY
                    reason = f"HANDLER_ERROR:{type(exc).__name__}"

        executed = decision == Decision.ALLOW and tool_result is not None
        emitted_evidence = [tool_result.evidence] if tool_result and tool_result.evidence else []
        recorded_evidence = emitted_evidence if emitted_evidence else evidence
        feedback = self._feedback(event_id, action, reason) if decision != Decision.ALLOW else None
        payload = {
            "schema_version": "drf_omtir_flight_recorder_event.v0.1",
            "event_id": event_id,
            "event_type": "action",
            "proposal": {"action": action, "arguments": arguments},
            "action_contract": self._rule_dict(rule),
            "authority": self._authority(
                "DRF_RULE",
                rule.name if rule else "NO_POLICY_RULE",
                decision.value,
                reason,
            ),
            "drf_decision": {
                "decision": decision.value,
                "allowed": decision == Decision.ALLOW,
                "reason": reason,
            },
            "execution": {
                "executed": executed,
                "status": "EXECUTED_TYPED_HANDLER" if executed else "NOT_EXECUTED",
            },
            "evidence_packet": self._evidence_packet(recorded_evidence),
            "tool_result": tool_result.to_dict() if tool_result else None,
            "feedback": feedback,
            "adaptation": self._adaptation(adapted_from_event_id, "typed_action_selected"),
        }
        record = self.wal.append(payload)
        return {
            "event_id": event_id,
            "decision": decision.value,
            "allowed": decision == Decision.ALLOW,
            "executed": executed,
            "reason": reason,
            "feedback": feedback,
            "record_hash": record["record_hash"],
            "tool_result": tool_result.to_dict() if tool_result else None,
        }

    def submit_claim(
        self,
        claim: str,
        *,
        requested_status: str,
        evidence_event_id: str | None = None,
        adapted_from_event_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = self.wal.next_event_id()
        requested_status = requested_status.upper()
        admitted = False
        decision = Decision.ALLOW
        reason = "HYPOTHESIS_RECORDED"
        evidence_sources: list[EvidenceRef] = []

        if requested_status not in {"HYPOTHESIS", "CONFIRMED"}:
            decision = Decision.DENY
            reason = "INVALID_REQUESTED_STATUS"
        elif requested_status == "CONFIRMED":
            evidence_sources, error = self._confirmed_claim_evidence(evidence_event_id)
            if error:
                decision = Decision.DENY
                reason = error
            else:
                admitted = True
                reason = "STRUCTURAL_EVIDENCE_PRESENT"

        status = "CONFIRMED" if admitted else (
            "HYPOTHESIS" if requested_status == "HYPOTHESIS" else "REJECTED_HYPOTHESIS"
        )
        linked = evidence_sources[0] if evidence_sources else None
        feedback = self._feedback(event_id, "submit_claim", reason) if decision == Decision.DENY else None
        payload = {
            "schema_version": "drf_omtir_flight_recorder_event.v0.1",
            "event_id": event_id,
            "event_type": "claim",
            "proposal": {
                "action": "submit_claim",
                "arguments": {
                    "claim": claim,
                    "requested_status": requested_status,
                    "evidence_event_id": evidence_event_id,
                },
            },
            "authority": self._authority(
                "OMTIR_RULE",
                self._claim_rule_name(requested_status, reason),
                decision.value,
                reason,
            ),
            "omtir_decision": {
                "decision": decision.value,
                "admitted": admitted,
                "reason": reason,
            },
            "execution": {"executed": False, "status": "CLAIM_ONLY"},
            "evidence_packet": self._evidence_packet(evidence_sources),
            "claim": {
                "text": claim,
                "requested_status": requested_status,
                "status": status,
                "admitted": admitted,
                "linked_tool_event_id": evidence_event_id if admitted else None,
                "linked_output_sha256": linked.output_sha256 if linked else None,
            },
            "feedback": feedback,
            "adaptation": self._adaptation(adapted_from_event_id, "claim_resubmitted"),
        }
        record = self.wal.append(payload)
        return {
            "event_id": event_id,
            "decision": decision.value,
            "admitted": admitted,
            "status": status,
            "reason": reason,
            "feedback": feedback,
            "record_hash": record["record_hash"],
        }

    def runtime_status(self) -> dict[str, Any]:
        records = self.wal.read()
        return {
            "policy_version": self.policy.version,
            "registered_tools": sorted(self.handlers),
            "allowed_executable_actions": self.policy.allowed_executable_actions(),
            "record_count": len(records),
            "last_record_hash": records[-1]["record_hash"] if records else None,
        }

    def _action_decision(self, rule: ActionRule | None, evidence: list[EvidenceRef]) -> tuple[Decision, str]:
        if rule is None:
            return self.policy.unknown_action_decision, "NO_POLICY_RULE"
        if rule.decision != Decision.ALLOW:
            return rule.decision, "POLICY_MATCH"
        present = {item.lane for item in evidence}
        if any(required not in present for required in rule.required_evidence_lanes):
            return Decision.DENY, "INSUFFICIENT_EVIDENCE"
        if not rule.executable:
            return Decision.DENY, "ACTION_NOT_EXECUTABLE"
        return Decision.ALLOW, "POLICY_MATCH"

    def _confirmed_claim_evidence(self, evidence_event_id: str | None) -> tuple[list[EvidenceRef], str | None]:
        if not evidence_event_id:
            return [], "CONFIRMED_CLAIM_REQUIRES_EVIDENCE_EVENT_ID"
        source = self.wal.get_payload(evidence_event_id)
        if not source:
            return [], "EVIDENCE_EVENT_NOT_FOUND"
        if not source.get("execution", {}).get("executed"):
            return [], "EVIDENCE_EVENT_NOT_EXECUTED"
        structural = []
        for item in source.get("evidence_packet", {}).get("sources", []):
            if item.get("lane") == EvidenceLane.STRUCTURAL.value and item.get("validation") == "VALID":
                structural.append(
                    EvidenceRef(
                        source=str(item["source"]),
                        lane=EvidenceLane.STRUCTURAL,
                        output_path=item.get("output_path"),
                        output_sha256=item.get("output_sha256"),
                        validation=str(item.get("validation", "UNKNOWN")),
                    )
                )
        if not structural:
            return [], "STRUCTURAL_EVIDENCE_REQUIRED"
        for item in structural:
            if not item.output_path or not item.output_sha256:
                return [], "STRUCTURAL_OUTPUT_LINK_REQUIRED"
            output = (self.root / item.output_path).resolve()
            try:
                output.relative_to(self.root)
            except ValueError:
                return [], "STRUCTURAL_OUTPUT_OUTSIDE_ROOT"
            if not output.exists():
                return [], "STRUCTURAL_OUTPUT_MISSING"
            if sha256_file(output) != item.output_sha256:
                return [], "STRUCTURAL_OUTPUT_HASH_MISMATCH"
        return structural, None

    def _feedback(self, event_id: str, action: str, reason: str) -> dict[str, Any]:
        return {
            "feedback_type": "governance_constraint",
            "feedback_version": "drf_omtir_flight_recorder_feedback.v0.1",
            "source_event_id": event_id,
            "original_action": action,
            "reason": reason,
            "allowed_alternatives": self.policy.allowed_executable_actions(),
        }

    @staticmethod
    def _adaptation(source_event_id: str | None, result: str) -> dict[str, Any] | None:
        if not source_event_id:
            return None
        return {"is_adaptive_retry": True, "adapted_from_event_id": source_event_id, "adaptation_result": result}

    @staticmethod
    def _rule_dict(rule: ActionRule | None) -> dict[str, Any] | None:
        if not rule:
            return None
        return {
            "name": rule.name,
            "effect": rule.effect.value,
            "decision": rule.decision.value,
            "required_evidence_lanes": [lane.value for lane in rule.required_evidence_lanes],
            "executable": rule.executable,
        }

    def _authority(self, source: str, rule_name: str, decision: str, reason: str) -> dict[str, Any]:
        return {
            "source": source,
            "rule": rule_name,
            "origin": f"{source}/{rule_name}",
            "policy_version": self.policy.version,
            "decision": decision,
            "reason": reason,
        }

    @staticmethod
    def _claim_rule_name(requested_status: str, reason: str) -> str:
        if requested_status not in {"HYPOTHESIS", "CONFIRMED"}:
            return "valid_claim_status_required"
        if requested_status == "CONFIRMED":
            if reason == "STRUCTURAL_EVIDENCE_PRESENT":
                return "confirmed_claim_requires_structural_evidence"
            return "confirmed_claim_requires_valid_structural_link"
        return "hypothesis_recording"

    @staticmethod
    def _evidence_packet(sources: list[EvidenceRef]) -> dict[str, Any]:
        return {
            "sources": [source.to_dict() for source in sources],
            "has_structural": any(source.lane == EvidenceLane.STRUCTURAL for source in sources),
            "has_reference": any(source.lane == EvidenceLane.REFERENCE for source in sources),
            "has_research_only": any(source.lane == EvidenceLane.RESEARCH_ONLY for source in sources),
            "has_unknown": any(source.lane == EvidenceLane.UNKNOWN for source in sources),
            "has_quarantined": any(source.lane == EvidenceLane.QUARANTINED for source in sources),
        }
