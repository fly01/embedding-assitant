from __future__ import annotations

from typing import Annotated, Any

from fastapi import Header

from .integrations import HostIntegrationManifest
from .models import HostContext, PendingAction
from .store import Store


async def host_context(
    actor_id: Annotated[str, Header(alias="X-Actor-ID")],
    scope_key: Annotated[str, Header(alias="X-Scope-Key")],
    denied_permissions: Annotated[str | None, Header(alias="X-Denied-Permissions")] = None,
) -> HostContext:
    denied = {permission.strip() for permission in denied_permissions.split(",")} if denied_permissions else set()
    return HostContext(actor_id=actor_id, scope_key=scope_key, denied_permissions=denied)


class ReferenceHostAdapter:
    def __init__(self, store: Store, manifest: HostIntegrationManifest):
        self.store = store
        self.manifest = manifest

    def page_context(self, host: HostContext) -> dict[str, Any]:
        return {
            "scope_key": host.scope_key,
            "record_count": len(self.store.list_host_records(host)),
        }

    def authorize(self, host: HostContext, permission: str) -> dict[str, Any]:
        return {
            "allowed": permission not in host.denied_permissions,
            "permission": permission,
            "actor_id": host.actor_id,
            "scope_key": host.scope_key,
        }

    def apply_action(self, host: HostContext, action: PendingAction) -> dict[str, Any]:
        if action.action_type == "attachment.promote":
            attachment_id = action.payload["attachment_id"]
            self.store.get_attachment(host, attachment_id)
            create_action = action.model_copy(
                update={
                    "action_type": "host_data.record.create",
                    "payload": {
                        "title": action.payload["title"],
                        "amount": action.payload.get("amount", 0),
                        "occurred_at": action.payload["occurred_at"],
                    },
                }
            )
            result = self.store.apply_host_record_action(host, create_action)
            promotion = self.store.record_attachment_promotion(host, attachment_id, result["record_id"])
            return {**result, **promotion}
        return self.store.apply_host_record_action(host, action)

    def refresh_data(self, host: HostContext) -> list[dict[str, Any]]:
        return self.store.list_host_records(host)
