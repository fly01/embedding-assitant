from __future__ import annotations

from typing import Any

from .errors import ConflictError, ValidationError
from .models import HostContext, PrivacyJob, PrivacyJobStatus, PrivacyRequest
from .store import Store


class PrivacyService:
    def __init__(self, store: Store):
        self.store = store

    def inventory(self, host: HostContext) -> list[dict[str, Any]]:
        return self.store.privacy_inventory(host)

    def export(self, host: HostContext, request: PrivacyRequest) -> PrivacyJob:
        data = self.store.export_privacy_data(host)
        categories = request.categories or list(data)
        unknown = set(categories).difference(data)
        if unknown:
            raise ValidationError(f"Unknown Privacy categories: {', '.join(sorted(unknown))}")
        selected = {category: data[category] for category in categories}
        manifest = {
            "schema_version": "0.1",
            "categories": categories,
            "scope": {"actor_id": host.actor_id, "scope_key": host.scope_key},
            "retention_restrictions": ["host_records"],
        }
        job = self.store.create_privacy_job(
            host,
            kind="export",
            scope={"categories": categories, "conversation_id": request.conversation_id},
            status=PrivacyJobStatus.COMPLETED,
            preview={"manifest": manifest},
            results=[{"status": "exported", "manifest": manifest, "data": selected}],
        )
        self._emit(job)
        return job

    def preview_deletion(self, host: HostContext, request: PrivacyRequest) -> PrivacyJob:
        inventory = {resource["category"]: resource for resource in self.inventory(host)}
        categories = request.categories or [
            category for category, resource in inventory.items() if resource["deletable"]
        ]
        unknown = set(categories).difference(inventory)
        if unknown:
            raise ValidationError(f"Unknown Privacy categories: {', '.join(sorted(unknown))}")
        impact = [inventory[category] for category in categories if category in inventory]
        if "host_records" in inventory:
            impact.append({**inventory["host_records"], "effect": "host_handoff"})
        job = self.store.create_privacy_job(
            host,
            kind="deletion",
            scope={"categories": categories, "conversation_id": request.conversation_id},
            status=PrivacyJobStatus.AWAITING_CONFIRMATION,
            preview={"impact": impact, "irreversible": True},
            results=[],
        )
        self._emit(job)
        return job

    def confirm_deletion(self, host: HostContext, job_id: str) -> PrivacyJob:
        job = self.store.get_privacy_job(host, job_id)
        if job.kind != "deletion" or job.status is not PrivacyJobStatus.AWAITING_CONFIRMATION:
            raise ConflictError("Privacy Job is not awaiting deletion confirmation")
        running = self.store.update_privacy_job(job.id, status=PrivacyJobStatus.RUNNING, results=[])
        self._emit(running)
        try:
            results = self.store.delete_privacy_categories(
                host,
                categories=job.scope["categories"],
                conversation_id=job.scope.get("conversation_id"),
            )
        except FileNotFoundError as error:
            partial = self.store.update_privacy_job(
                job.id,
                status=PrivacyJobStatus.PARTIAL,
                results=[{"status": "failed", "error": str(error)}],
            )
            self._emit(partial)
            return partial
        completed = self.store.update_privacy_job(
            job.id,
            status=PrivacyJobStatus.COMPLETED,
            results=results,
        )
        self._emit(completed)
        return completed

    def retry(self, host: HostContext, job_id: str) -> PrivacyJob:
        job = self.store.get_privacy_job(host, job_id)
        if job.status not in {PrivacyJobStatus.PARTIAL, PrivacyJobStatus.FAILED}:
            raise ConflictError("Only partial or failed Privacy Jobs can be retried")
        awaiting = self.store.update_privacy_job(
            job.id,
            status=PrivacyJobStatus.AWAITING_CONFIRMATION,
            results=job.results,
        )
        return self.confirm_deletion(host, awaiting.id)

    def _emit(self, job: PrivacyJob) -> None:
        self.store.append_event(
            scope_kind="privacy_job",
            scope_id=job.id,
            event_type="privacy.job.updated",
            payload={"job": job.model_dump(mode="json")},
        )
