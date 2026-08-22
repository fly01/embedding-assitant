from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .integrations import HostIntegrationManifest
from .models import ActionState, ExecutionMode, HostContext

FORCED_CONFIRMATION_OPERATIONS = {"delete", "link", "unlink", "promote"}
DANGEROUS_ACTIONS = {"payment", "transfer"}


@dataclass(frozen=True)
class PolicyDecision:
    state: ActionState
    evidence: dict[str, Any]


class PolicyEngine:
    version = "0.1"

    def __init__(self, manifest: HostIntegrationManifest):
        self.manifest = manifest

    def decide(
        self,
        *,
        host: HostContext,
        action_type: str,
        payload: dict[str, Any],
        mode: ExecutionMode,
    ) -> PolicyDecision:
        rule = self.manifest.action_rule(action_type)
        operation = action_type.rsplit(".", 1)[-1]
        reason: str

        if "records.write" in host.denied_permissions:
            state = ActionState.BLOCKED
            reason = "permission_denied"
        elif action_type in DANGEROUS_ACTIONS:
            state = ActionState.BLOCKED
            reason = "dangerous_capability_unavailable"
        elif mode is ExecutionMode.READ_ONLY:
            state = ActionState.BLOCKED
            reason = "read_only_mode"
        elif rule is None:
            state = ActionState.BLOCKED
            reason = "action_not_declared"
        elif operation in FORCED_CONFIRMATION_OPERATIONS or rule.risk == "high":
            state = ActionState.AWAITING_CONFIRMATION
            reason = "forced_confirmation"
        elif mode is ExecutionMode.AUTO_APPLY_ALLOWLIST and rule.auto_apply_eligible and rule.compensation:
            state = ActionState.AUTO_APPLYING
            reason = "reviewed_allowlist"
        else:
            state = ActionState.AWAITING_CONFIRMATION
            reason = "default_confirmation"

        return PolicyDecision(
            state=state,
            evidence={
                "policy_version": self.version,
                "actor_id": host.actor_id,
                "scope_key": host.scope_key,
                "mode": mode,
                "action_type": action_type,
                "risk": rule.risk if rule else "unknown",
                "reason": reason,
                "payload_fields": sorted(payload),
            },
        )
