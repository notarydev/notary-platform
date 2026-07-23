"""Evaluator registry — contract registration, lookup, and version resolution."""

from __future__ import annotations

from notary_platform.sweep.models import EvaluatorContractRecord


class EvaluatorRegistry:
    """Registry of evaluator contracts.

    In the initial implementation, contracts are stored in the storage
    backend. Future versions may load evaluator code implementations.
    """

    def __init__(self, storage: Any) -> None:  # noqa: ANN401
        self._storage = storage

    def register(self, contract: EvaluatorContractRecord) -> EvaluatorContractRecord:
        return self._storage.create_evaluator_contract(contract)

    def get(self, evaluator_id: str) -> EvaluatorContractRecord | None:
        return self._storage.get_evaluator_contract(evaluator_id)

    def get_version(self, evaluator_id: str, version: str) -> EvaluatorContractRecord | None:
        contract = self._storage.get_evaluator_contract(evaluator_id)
        if contract is not None and contract.version == version:
            return contract
        return None

    def list(self, org_id: str) -> list[EvaluatorContractRecord]:
        return self._storage.list_evaluator_contracts(org_id)

    def check_prerequisites(
        self, evaluator_id: str, available_prerequisites: set[str]
    ) -> tuple[bool, list[str]]:
        contract = self._storage.get_evaluator_contract(evaluator_id)
        if contract is None:
            return False, ["evaluator_not_found"]
        missing = [p for p in contract.required_prerequisites if p not in available_prerequisites]
        if missing:
            return False, missing
        return True, []
