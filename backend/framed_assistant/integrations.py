from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IntegrationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HostDataEntity(IntegrationModel):
    writable_fields: list[str]
    row_scope: str
    optimistic_lock: str


class HostDataTools(IntegrationModel):
    enabled: bool = False
    operations: list[str] = Field(default_factory=list)
    entities: dict[str, HostDataEntity] = Field(default_factory=dict)


class ActionRule(IntegrationModel):
    action_type: str
    risk: str
    auto_apply_eligible: bool
    compensation: str | None = None


class HostIntegrationManifest(IntegrationModel):
    schema_version: str
    application_id: str
    review_status: str
    host_data_tools: HostDataTools
    action_rules: list[ActionRule]

    def action_rule(self, action_type: str) -> ActionRule | None:
        return next((rule for rule in self.action_rules if rule.action_type == action_type), None)


REFERENCE_MANIFEST = HostIntegrationManifest(
    schema_version="0.1",
    application_id="org.example.reference-host",
    review_status="approved",
    host_data_tools=HostDataTools(
        enabled=True,
        operations=["create", "update", "upsert", "delete", "link", "unlink"],
        entities={
            "record": HostDataEntity(
                writable_fields=["title", "amount", "occurred_at", "record_id", "target_id", "version"],
                row_scope="current_actor",
                optimistic_lock="version",
            )
        },
    ),
    action_rules=[
        ActionRule(
            action_type="host_data.record.create",
            risk="low",
            auto_apply_eligible=True,
            compensation="delete_created_record",
        ),
        ActionRule(
            action_type="host_data.record.update",
            risk="low",
            auto_apply_eligible=True,
            compensation="restore_previous_record",
        ),
        ActionRule(action_type="host_data.record.upsert", risk="medium", auto_apply_eligible=False),
        ActionRule(action_type="host_data.record.delete", risk="high", auto_apply_eligible=False),
        ActionRule(action_type="host_data.record.link", risk="medium", auto_apply_eligible=False),
        ActionRule(action_type="host_data.record.unlink", risk="medium", auto_apply_eligible=False),
        ActionRule(action_type="attachment.promote", risk="high", auto_apply_eligible=False),
        ActionRule(action_type="sample.records.create", risk="medium", auto_apply_eligible=False),
    ],
)
